import cv2
import numpy as np
from scipy.stats import mode
from sklearn.cluster import KMeans

import ffmpeg


def check_rotation(path_video_file):
    # this returns meta-data of the video file in form of a dictionary
    meta_dict = ffmpeg.probe(path_video_file)

    print(meta_dict)

    # from the dictionary, meta_dict['streams'][0]['tags']['rotate'] is the key
    # we are looking for
    rotateFromMetadata = None
    screenRotate = None

    effectiveRotate = 0.0

    for idx, stream in enumerate(meta_dict['streams']):
        if stream.get('codec_type') == 'video':
            if 'tags' in stream:
                if 'rotate' in stream['tags']:
                    rotateFromMetadata = int(stream['tags']['rotate'])
                    break

    for idx, stream in enumerate(meta_dict['streams']):
        if stream.get('codec_type') == 'video':
            if 'side_data_list' in stream:
                if 'rotation' in stream['side_data_list']:
                    screenRotate = int(stream['side_data_list']['rotation'])
                    break


    if rotateFromMetadata is not None:
        effectiveRotate += rotateFromMetadata

    if screenRotate is not None:
        # it's minus here, cause matrix rotation means actual orientation
        # of the matrix, thus, we need to compensate it.
        effectiveRotate += -screenRotate

    if effectiveRotate == 90:
        return cv2.ROTATE_90_CLOCKWISE
    elif effectiveRotate == 180:
        return cv2.ROTATE_180
    elif effectiveRotate == 270:
        return cv2.ROTATE_90_COUNTERCLOCKWISE


def correct_rotation(frame, rotateCode):  
     return cv2.rotate(frame, rotateCode)


def verify_video(video_path, direction, second_direction, verbose=False):
    target_movement_angle = second_direction - direction
    # max error between target and actual movement angle
    allowed_error = 20

    # Read the video 
    cap = cv2.VideoCapture(video_path)
 
    # Parameters for ShiTomasi corner detection
    feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
 
    # Parameters for Lucas Kanade optical flow
    lk_params = dict(
        winSize=(15, 15),
        maxLevel=2,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
    )
 
    # Create random colors
    color = np.random.randint(0, 255, (100, 3))
 
     # check if video requires rotation
    rotateCode = check_rotation(video_path)

    # Take first frame and find corners in it
    ret, old_frame = cap.read()
    old_gray = cv2.cvtColor(old_frame, cv2.COLOR_BGR2GRAY)

    if rotateCode is not None:
        old_gray = correct_rotation(old_gray, rotateCode)

    p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)

    width = old_frame.shape[1]
    height = old_frame.shape[0]
    one_width_angle = 180 / 4
    one_height_angle = 180 / 5

    x_movement = 0
    y_movement = 0

    in_direction_time = 0
    in_second_direction_time = 0
 
    # Create a mask image for drawing purposes
    mask = np.zeros_like(old_frame)

    prev_time = 0.0
    current_time = 0.0
    in_direction = True
    in_second_direction = False

    while True:
        # Read new frame
        ret, frame = cap.read()

        if rotateCode is not None:
            frame = correct_rotation(frame, rotateCode)

        prev_time = current_time
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC)
        if not ret:
            break
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
        # Calculate Optical Flow
        p1, st, err = cv2.calcOpticalFlowPyrLK(
            old_gray, frame_gray, p0, None, **lk_params
        )
        # Select good points
        if(p1 is None):
            p0 = cv2.goodFeaturesToTrack(old_gray, mask=None, **feature_params)
            continue

        good_new = p1[st == 1]
        good_old = p0[st == 1]
    
        x_deltas = []
        y_deltas = []

        # Draw the tracks
        for i, (new, old) in enumerate(zip(good_new, good_old)):
            x1, y1 = new.ravel()
            x2, y2 = old.ravel()
            x_deltas.append(x2 - x1)
            y_deltas.append(y1 - y2)

            # only needed for visualization
            if verbose:
                mask = cv2.line(mask, (int(x1), int(y1)), (int(x2), int(y2)), color[i].tolist(), 2)
                frame = cv2.circle(frame, (int(x1), int(y1)), 5, color[i].tolist(), -1)

        if(len(x_deltas) > 0):
            avg_x_delta = sum(x_deltas) / len(x_deltas)
            x_movement += avg_x_delta
            movement_x_angle = x_movement / width * one_width_angle
            # print('x_movement:', movement_x_angle)

            avg_y_delta = sum(y_deltas) / len(y_deltas)
            y_movement += avg_y_delta
            movement_y_angle = y_movement / height * one_height_angle
            # print('y_movement:', movement_y_angle)

            in_direction = abs(movement_y_angle - 0) < 30 and abs(movement_x_angle - 0) < 20
            in_second_direction = abs(movement_y_angle - 0) < 30 and abs(movement_x_angle - target_movement_angle) < 20

        # weird but happens sometimes
        if current_time > prev_time:
            if in_direction:
                in_direction_time += current_time - prev_time

            if in_second_direction:
                in_second_direction_time += current_time - prev_time

        # print('in_direction_time: ', in_direction_time, 'in_second_direction_time: ', in_second_direction_time, )
    
        # only needed for visualization
        if verbose:
            # Display the demo
            img = cv2.add(frame, mask)
            cv2.imshow("frame", img)

            k = cv2.waitKey(25) & 0xFF
            if k == 27:
                break
    
        # Update the previous frame and previous points
        old_gray = frame_gray.copy()
        p0 = good_new.reshape(-1, 1, 2)

    return in_direction_time > 5000 and in_second_direction_time > 1000, round(in_direction_time, 2), round(in_second_direction_time, 2), rotateCode


if __name__ == '__main__':
    # verify_video('https://ipfs.objective.camera/QmaaSwJEg85fGka8PJ65U3MSXbknmdzUu7w1LguoJLk5Xs', 198, 100)
    # verify_video('/Users/alex/projects/my/chainlink/objective_backend/QmaaSwJEg85fGka8PJ65U3MSXbknmdzUu7w1LguoJLk5Xs.mp4', 198, 100)

    # -rw-r--r--@  1 alex  staff  39600665 Nov 15 12:20 QmPKP2tn7UP9B2EkLUNZwL7NTqAT3RyR5P7y56mFtsTUp9.mp4
    # -rw-r--r--@  1 alex  staff  30928163 Nov 15 20:46 QmPWhpsGM7zgMXrc3sSehJK4XQCrataXVkryw7yF2HZvXs.mp4
    # -rw-r--r--@  1 alex  staff  30492749 Nov 15 20:47 QmTE69pWvdadKBJkTk4F2RqYi2vD4bMyKZqVbSXqDH9HuK.mp4
    # -rw-r--r--@  1 alex  staff  26689309 Nov 15 20:46 QmaaSwJEg85fGka8PJ65U3MSXbknmdzUu7w1LguoJLk5Xs.mp4

    base_path = '/Users/alex/projects/my/chainlink/objective_backend/'

    #lucas_kanade_method(video_path)
    # print('verified:', verify_video(f'{base_path}/QmaaSwJEg85fGka8PJ65U3MSXbknmdzUu7w1LguoJLk5Xs.mp4', 198, 100))
    # print('verified:', verify_video(f'{base_path}/QmPWhpsGM7zgMXrc3sSehJK4XQCrataXVkryw7yF2HZvXs.mp4', 224, 100))
    # print('verified:', verify_video(f'{base_path}/QmTE69pWvdadKBJkTk4F2RqYi2vD4bMyKZqVbSXqDH9HuK.mp4', 0, 100))

    print('verified:', verify_video(f'{base_path}/QmTE69pWvdadKBJkTk4F2RqYi2vD4bMyKZqVbSXqDH9HuK.mp4', 0, 100))

    # method = cv2.optflow.calcOpticalFlowSparseToDense
    # dense_optical_flow(method, video_path, to_gray=True)
