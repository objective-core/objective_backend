// SPDX-License-Identifier: MIT
pragma solidity 0.8.13;

import 'https://github.com/smartcontractkit/chainlink/blob/master/contracts/src/v0.8/ChainlinkClient.sol';
import 'https://github.com/smartcontractkit/chainlink/blob/master/contracts/src/v0.8/ConfirmedOwner.sol';
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/Strings.sol";
 
contract VideoRequester is ChainlinkClient, ConfirmedOwner {
    using Chainlink for Chainlink.Request;

    bytes32 private jobId;
    uint256 private fee;
    uint private idCounter;

    struct VideoRequest {
        uint requestId;
        address requester;
        uint32 lat;
        uint32 long;
        uint32 start;
        uint32 end;
        uint16 direction;
        uint reward;
        bytes32 chainlinkRequestId;
        string cid;
        address uploader;
    }

    event VideoRequested(
        uint requestId,
        address requester,
        uint32 lat,
        uint32 long,
        uint32 start,
        uint32 end,
        uint16 direction,
        uint reward
    );
    event VideoReceived(
        uint requestId,
        string cid,
        address uploader
    );

    mapping (uint => VideoRequest) requests;
    mapping (bytes32 => uint) chainlinkRequestIdToVideoRequestId;
 
    constructor() ConfirmedOwner(msg.sender) {
        // Goerli testnet
        setChainlinkToken(0x326C977E6efc84E512bB9C30f76E30c160eD06FB);
        setChainlinkOracle(0xCC79157eb46F5624204f47AB42b3906cAA40eaB7);
    
        // source of job id: https://docs.chain.link/docs/any-api/testnet-oracles/
        jobId = '7da2702f37fd48e5b1b9a5715e3509b6'; // bytes job
        fee = (1 * LINK_DIVISIBILITY) / 10; // 0,1 * 10**18 (Varies by network and job)

        idCounter = 1;
    }

    function submitRequest(uint32 lat, uint32 long, uint32 start, uint32 end, uint16 direction) payable external {
        requests[idCounter] = VideoRequest(idCounter, msg.sender, lat, long, start, end, direction, msg.value, "", "", address(0));

        emit VideoRequested(idCounter, msg.sender, lat, long, start, end, direction, msg.value);

        idCounter++;
    }

    function checkRequest(uint id) public {
        // We only allow to call one checkRequest per time.
        if(requests[id].chainlinkRequestId == "") {
            Chainlink.Request memory req = buildChainlinkRequest(jobId, address(this), this.fulfillVideoRequest.selector);

            string memory url = string.concat("https://api.objective.camera/video/", Strings.toString(id));

            req.add('get', url);
            req.add('path', 'abi');

            bytes32 requestId = sendChainlinkRequest(req, fee);

            // We use this field as a lock, to make sure nobody does parallel
            // requests for the same video. Otherwise, we might end up with
            // doublespend.
            requests[id].chainlinkRequestId = requestId;

            // We use this map to make sure contract processes exactly
            // the same VideoRequest in fullfill.
            chainlinkRequestIdToVideoRequestId[requestId] = id;
        }
    }

    function fulfillVideoRequest(
        bytes32 _requestId,
        bytes calldata data
    ) public recordChainlinkFulfillment(_requestId) {
        uint videoRequestId = chainlinkRequestIdToVideoRequestId[_requestId];
        VideoRequest storage videoRequest = requests[videoRequestId];

        (videoRequest.uploader, videoRequest.cid) = decode(data);

        bool sent;

        // Refund, since backend returns empty uploader.
        if(videoRequest.uploader == address(0)) {
            (sent,) = videoRequest.requester.call{value: videoRequest.reward}("");
            require(sent, "Failed to send Ether");
            return;
        } else {
            (sent,) = videoRequest.uploader.call{value: videoRequest.reward}("");
            require(sent, "Failed to send Ether");

            emit VideoReceived(videoRequest.requestId, videoRequest.cid, videoRequest.uploader);
        }
    }

    function getCid(uint id) public view returns (string memory cid) {
        VideoRequest memory request = requests[id];
        cid = request.cid;
    }

    function dropChainlinkRequestId(uint id) public onlyOwner {
        if(requests[id].chainlinkRequestId != "") {
            VideoRequest storage request = requests[id];
            request.chainlinkRequestId = "";
        }
    }

    function decode(bytes memory data) public pure returns (address addr, string memory cid) {
        (addr, cid) = abi.decode(data, (address, string));
    }
}
