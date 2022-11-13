// SPDX-License-Identifier: MIT
pragma solidity 0.8.13;

import 'https://github.com/smartcontractkit/chainlink/blob/master/contracts/src/v0.8/ChainlinkClient.sol';
import 'https://github.com/smartcontractkit/chainlink/blob/master/contracts/src/v0.8/ConfirmedOwner.sol';
 
contract VideoRequester is ChainlinkClient, ConfirmedOwner {
    using Chainlink for Chainlink.Request;

    bytes32 private jobId;
    uint256 private fee;

    struct VideoRequest { 
        string request_id;
        uint32 lat;
        uint32 long;
        uint32 start;
        uint32 stop;
        uint16 direction;
        uint reward;
        string url;
        address requester;
    }

    event VideoRequested(address requester, uint32 lat, uint32 long, uint32 start, uint32 end, uint16 direction, uint reward);
    event VideoReceived(string url);

    mapping (string => VideoRequest) requests;
 
    constructor() ConfirmedOwner(msg.sender) {
        setChainlinkToken(0x326C977E6efc84E512bB9C30f76E30c160eD06FB);
        setChainlinkOracle(0xCC79157eb46F5624204f47AB42b3906cAA40eaB7);
    
        jobId = '53f9755920cd451a8fe46f5087468395';
        fee = (1 * LINK_DIVISIBILITY) / 10; // 0,1 * 10**18 (Varies by network and job)
    }

    function submitRequest (string memory id, uint32 lat, uint32 long, uint32 start, uint32 end, uint16 direction) payable external {
        emit VideoRequested(msg.sender, lat, long, start, end, direction, msg.value);

        requests[id] = VideoRequest(id, lat, long, start, end, direction, msg.value, "", msg.sender);
    }

    function checkRequest(string calldata id) public {
        Chainlink.Request memory req = buildChainlinkRequest(jobId, address(this), this.fulfillVideoRequest.selector);

        string memory url = string.concat("https://api.objective.camera/video/", id);

        req.add('urlCID', url);
        req.add('pathCID', 'cid');
        req.add('urlRequest', url);
        req.add('pathRequest', 'request');
        req.add('urlUploader', url);
        req.add('pathUploader', 'uploader');

        sendChainlinkRequest(req, fee);
    }

    function fulfillVideoRequest(
        bytes32 _requestId,
        string calldata videoCID,
        string calldata videoRequestId,
        address payable _videoUploader
    ) public recordChainlinkFulfillment(_requestId) {
        if (bytes(videoCID).length == 0)
            revert("Could not verify video.");

        VideoRequest storage request = requests[videoRequestId];
        request.url = videoCID;

        emit VideoReceived(request.url);
    }

    function getUrl(string memory id) public view returns (string memory url) {
        VideoRequest memory request = requests[id];
        url = request.url;
    }
}