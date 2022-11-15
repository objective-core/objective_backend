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
        uint request_id;
        address requester;
        uint32 lat;
        uint32 long;
        uint32 start;
        uint32 end;
        uint16 direction;
        uint reward;
        bytes32 chainlink_request_id;
        string cid;
        address uploader;
    }

    event VideoRequested(
        uint request_id,
        address requester,
        uint32 lat,
        uint32 long,
        uint32 start,
        uint32 end,
        uint16 direction,
        uint reward
    );
    event VideoReceived(
        uint request_id,
        string cid,
        address uploader
    );

    mapping (uint => VideoRequest) requests;
    mapping (bytes32 => uint) chainlinkIdToRequestId;
 
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
        requests[idCounter] = VideoRequest(idCounter, msg.sender, lat, long, start, end, direction, msg.value, "1", "1", address(0));

        emit VideoRequested(idCounter, msg.sender, lat, long, start, end, direction, msg.value);

        idCounter++;
    }

    function checkRequest(uint id) public {
        // We only allow to call one checkRequest per time.
        if(requests[id].chainlink_request_id == "") {
            Chainlink.Request memory req = buildChainlinkRequest(jobId, address(this), this.fulfillVideoRequest.selector);

            string memory url = string.concat("https://api.objective.camera/video/", Strings.toString(id));

            req.add('get', url);
            req.add('path', 'abi');

            bytes32 requestId = sendChainlinkRequest(req, fee);

            requests[id].chainlink_request_id = requestId;
            chainlinkIdToRequestId[requestId] = id;
        }
    }

    // can anybody call me?
    function fulfillVideoRequest(
        bytes32 _requestId,
        bytes calldata data
    ) public recordChainlinkFulfillment(_requestId) {
        uint videoRequestId = chainlinkIdToRequestId[_requestId];
        VideoRequest storage videoRequest = requests[videoRequestId];

        (videoRequest.uploader, videoRequest.cid) = decode(data);

        (bool sent,) = videoRequest.uploader.call{value: videoRequest.reward}("");
        require(sent, "Failed to send Ether");

        emit VideoReceived(videoRequest.request_id, videoRequest.cid, videoRequest.uploader);
    }

    function getCid(uint id) public view returns (string memory cid) {
        VideoRequest memory request = requests[id];
        cid = request.cid;
    }

    // example of encoding to abi
    function encode(address addr, string memory cid) public pure returns (bytes memory) {
        return (abi.encode(addr, cid));
    }

    function decode(bytes memory data) public pure returns (address addr, string memory cid) {
        (addr, cid) = abi.decode(data, (address, string));
    }
}
