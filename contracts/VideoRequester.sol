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
        uint lat;
        uint long;
        uint start;
        uint stop;
        uint reward;
        string url;
        address requester;
    }

    event VideoRequested(address requester, uint lat, uint long, uint start, uint end, uint reward);
    event VideoReceived(string url);

    mapping (string => VideoRequest) requests;
 
    constructor() ConfirmedOwner(msg.sender) {
        setChainlinkToken(0x326C977E6efc84E512bB9C30f76E30c160eD06FB);
        setChainlinkOracle(0xCC79157eb46F5624204f47AB42b3906cAA40eaB7);
    
        jobId = 'ca98366cc7314957b8c012c72f05aeeb';
        fee = (1 * LINK_DIVISIBILITY) / 10; // 0,1 * 10**18 (Varies by network and job)
    }
 
    function submitRequest (string memory id, uint lat, uint long, uint start, uint end) payable external {
        emit VideoRequested(msg.sender, lat, long, start, end, msg.value);
    
        requests[id] = VideoRequest(id, lat, long, start, end, msg.value, "", msg.sender);
    }

    function checkRequest(string memory id) public {
        VideoRequest storage request = requests[id];

        Chainlink.Request memory req = buildChainlinkRequest(jobId, address(this), this.fulfillVideoRequest.selector);

        string memory url = string.concat("https://635bc558aa7c3f113dc5c143.mockapi.io/api/v1/videos/", request.request_id);

        req.add('getURL', url);
        req.add('pathURL', 'url');

        req.add('getID', url);
        req.add('pathID', 'id');

        sendChainlinkRequest(req, fee);
    }

    function fulfillVideoRequest(
        bytes32 requestId,
        string memory urlResponse,
        string memory idResponse
    ) public recordChainlinkFulfillment(requestId) {
        VideoRequest storage request = requests[idResponse];
        request.url = urlResponse;

        emit VideoReceived(request.url);
    }

    function getUrl(string memory id) public view returns (string memory url) {
        VideoRequest memory request = requests[id];
        url = request.url;
    }
}

