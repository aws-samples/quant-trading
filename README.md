<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">

  <h3 align="center">AWS Quant Project</h3>

  <p align="center">
    Description
    <br />
    <a href="https://github.com/othneildrew/Best-README-Template"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/othneildrew/Best-README-Template">View Demo</a>
    ·
    <a href="https://github.com/othneildrew/Best-README-Template/issues">Report Bug</a>
    ·
    <a href="https://github.com/othneildrew/Best-README-Template/issues">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#initial-setup">Initial Setup</a></li>
        <li><a href="#cdk-deployment">CDK Deployment</a></li>
        <li><a href="#adding-api-key">Adding API Key</a></li>
        <li><a href="#looking-at-the-results">Looking at the Results</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

![Architecture Diagram of Installation][product-screenshot1]
![Architecture Diagram of Operational View][product-screenshot2]

About the project...

This is a codebase to initialize the underlying infrastructure and stacks needed for real time quantitative trading as well as the basic application level logic. As a quant, your job is to focus on quantitative logic, the reality is that you have to worry about underlying infrastructure and a lot of different layers when deploying solutions. For example, where to run, how to achieve elasticity, etc. This repository and the event-driven infrastructure provided aim to provide a quick start and entry point into your own quantitative work and to help alleviate these challenges. The solution helps take care of SDLC, market data durability, market data connectivity, DevOps (elasticity), as well as the management of the underlying infrastructure. We use P&L calculations just as an example, but we'll leave the secret sauce up to you.

This real time market portfolio application on AWS is setup through the [AWS CDK](https://aws.amazon.com/cdk/). The deployed CDK infrastructure comes with an example portfolio of the S&P 500 based on intraday momentum. The intraday momentum pattern says that the first half-hour return on the market since the previous day’s market close will predict the last half-hour return. This predictability will be stronger on more volatile days, on higher volume days, on recession days, and on major macroeconomic news release days.


<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

How to get started. This project is deployed using the AWS CDK.

### Initial Setup

You will use [AWS Cloud9](https://aws.amazon.com/cloud9/) as the IDE to setup the code and deploy the CDK environment. You can also use a different IDE if you’d prefer.

1. Navigate to the **AWS Cloud9** console and press **Create environment**.
2. Enter a name - **MarketPortfolioEnv**.
3. Use a **t2.micro** instance type.
4. Leave all other settings as default and choose **Create**.
5. After a few minutes, the environment should be created. Under **Cloud9 IDE**, press **Open**.
6. In the command line at the bottom, clone the [Git repository](https://github.com/aws-samples/quant-trading) using the following command:
  ```sh
  git clone https://github.com/aws-samples/quant-trading.git
  ```


### CDK Deployment

Now that the environment is setup, let’s deploy the application using the CDK. You’ll need to run a few commands to get everything set up for the CDK, this will allow for the entire application to be spun up through the CDK

1. In the **Cloud9 CLI**, type in the following commands to navigate to the CDK portion of the code and install the necessary dependencies
  ```sh
  cd AWSQuant/aws-quant-infra/deployment/cdk &&
  npm install
  ```
2. Use this command to bootstrap the environment:
  ```sh
  cdk bootstrap
  ```
3. This command is needed to download a required Lambda layer for AppConfig.
  ```sh
  sudo yum install jq -y &&
  aws lambda get-layer-version-by-arn —arn arn:aws:lambda:us-east-1:027255383542:layer:AWS-AppConfig-Extension:110 | jq -r '.Content.Location' | xargs curl -o ../../src/lambda/extension.zip
  ```
4. Now, to deploy the application using the CDK code enter this command:
  ```sh
  cdk deploy --all
  ```

*Note*: if you get an error saying the docker build failed and says “no space left on device” run this command:
  ```sh
  chmod +x ./../../src/utils/resize_root.sh &&
  ./../../src/utils/resize_root.sh 50
  ```

*Note*: If you get an error from creating the DynamoDB replica instance in the DB stack, you’ll need to go to the DynamoDB console and delete the replica from the console, then redeploy the CDK stack.



### Adding API Key

You can have data come in from either IEX or B-PIPE (Bloomberg Market Data Feed). In this section, you’ll enter the API key in Secrets Manager and that will enable the Intraday Momentum application to start working and allow the data to flow in from the market data feed.

1. Navigate to the **AWS Secrets Manager** console.
2. You should see two secrets created: `api_token_pk_sandbox` and `api_token_pk`.

![Secrets Manager Keys][secrets-manager]

3. Select `api_token_pk`.
4. Scroll down to the section that says **Secret value** and towards the right, select **Retrieve secret value**.

![Secret Value][secret-value]

5. Then, choose **Edit** and paste in your IEX or B-PIPE API key.
6. Press **Save**.


### Looking at the Results

You can view the results of the Intraday Momentum application after the day end by going to the DynamoDB table.


1. Navigate to the **AWS DynamoDB** console.
2. On the left, select **Tables** and then choose the table called `MvpPortfolioMonitoringPortfolioTable`.
3. Then, press the orange button in the top right that says **Explore table items**.

![DynamoDB Table Items][dynamodb-table-items]

4. You should then see data populated at the bottom under **Items returned**.

*Note*: If you don’t see any data, select the orange **Run** button to scan the table and retrieve the data.

5. If you’d like to analyze this data further, you can download it in CSV format by selecting **Actions**, then **Download results to CSV**.



<!-- USAGE EXAMPLES -->
## Usage

Add additional screenshots, code examples and demos...

_For more examples, please refer to the [Documentation](https://example.com)_

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [x] Add Changelog
- [x] Add back to top links
- [ ] Add Additional Templates w/ Examples
- [ ] Add "components" document to easily copy & paste sections of the readme
- [ ] Multi-language Support
    - [ ] Chinese
    - [ ] Spanish

See the [open issues](https://github.com/othneildrew/Best-README-Template/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

This section should list any major frameworks/libraries used to bootstrap your project. Leave any add-ons/plugins for the acknowledgements section. Here are a few examples.

* [![CDK][aws-cdk]][cdk-url]
* [![React][React.js]][React-url]
* [![Vue][Vue.js]][Vue-url]
* [![Angular][Angular.io]][Angular-url]
* [![Svelte][Svelte.dev]][Svelte-url]
* [![Laravel][Laravel.com]][Laravel-url]
* [![Bootstrap][Bootstrap.com]][Bootstrap-url]
* [![JQuery][JQuery.com]][JQuery-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Your Name - [@your_twitter](https://twitter.com/your_username) - email@example.com

Project Link: [https://github.com/your_username/repo_name](https://github.com/your_username/repo_name)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Use this space to list resources you find helpful and would like to give credit to. I've included a few of my favorites to kick things off!

* [Choose an Open Source License](https://choosealicense.com)
* [GitHub Emoji Cheat Sheet](https://www.webpagefx.com/tools/emoji-cheat-sheet)
* [Malven's Flexbox Cheatsheet](https://flexbox.malven.co/)
* [Malven's Grid Cheatsheet](https://grid.malven.co/)
* [Img Shields](https://shields.io)
* [GitHub Pages](https://pages.github.com)
* [Font Awesome](https://fontawesome.com)
* [React Icons](https://react-icons.github.io/react-icons/search)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/othneildrew/Best-README-Template.svg?style=for-the-badge
[contributors-url]: https://github.com/aws-samples/quant-trading/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/othneildrew/Best-README-Template.svg?style=for-the-badge
[forks-url]: https://github.com/aws-samples/quant-trading/network/members
[stars-shield]: https://img.shields.io/github/stars/othneildrew/Best-README-Template.svg?style=for-the-badge
[stars-url]: https://github.com/aws-samples/quant-trading/stargazers
[issues-shield]: https://img.shields.io/github/issues/othneildrew/Best-README-Template.svg?style=for-the-badge
[issues-url]: https://github.com/aws-samples/quant-trading/issues
[license-shield]: https://img.shields.io/github/license/othneildrew/Best-README-Template.svg?style=for-the-badge
[license-url]: https://github.com/othneildrew/Best-README-Template/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/sam-farber/
[product-screenshot1]: assets/AWS_Quant_Real_Time_Operational_View.drawio.png
[product-screenshot2]: assets/AWS_Quant_Real_Time_Installation.drawio.png
[secrets-manager]: assets/installation/secrets_manager.png
[secret-value]: assets/installation/secret_value.png
[dynamodb-table-items]: assets/installation/dynamodb_table_items.png
[aws-cdk]: https://img.shields.io/badge/-AWS%20CDK-orange
[cdk-url]: https://aws.amazon.com/cdk/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Vue.js]: https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D
[Vue-url]: https://vuejs.org/
[Angular.io]: https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white
[Angular-url]: https://angular.io/
[Svelte.dev]: https://img.shields.io/badge/Svelte-4A4A55?style=for-the-badge&logo=svelte&logoColor=FF3E00
[Svelte-url]: https://svelte.dev/
[Laravel.com]: https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white
[Laravel-url]: https://laravel.com
[Bootstrap.com]: https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white
[Bootstrap-url]: https://getbootstrap.com
[JQuery.com]: https://img.shields.io/badge/jQuery-0769AD?style=for-the-badge&logo=jquery&logoColor=white
[JQuery-url]: https://jquery.com
