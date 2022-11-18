# Objective Camera Backend

Objective Camera is a [Chainlink Fall 2022 Hackathon](https://chainlinkfall2022.devpost.com) project.
It aims to build a tamper proof mobile camera application and video distribution channel using Web3 technology stack.
For more detail see the [hackaton submission](https://devpost.com/software/objective).

_Disclaimer: this project is a quick and dirty implementation of the Objective Camera backend and is not ready for production use._

The purpose of the backend is the following:
* Pull `VideoRequested` events from [Solidity smart contract](contracts/VideoRequester.sol) and index them into a Postgres database.
* Expose video requests via a public HTTP API.
* Verify that uploaded video matches the video request.
* Call `checkRequest` function of the contract upon successful video upload.
* Generate thumbnails for uploaded videos.

## License

This project is licensed under the Apache License 2.0 License - see the [LICENSE](LICENSE) file for details.
