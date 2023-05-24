# Serverless Framework with JavaScript

---

Example project using the [Serverless Framework](https://serverless.com), JavaScript, AWS Lambda, AWS API Gateway and GitLab Pages.

---

## Deployment
---

### Secrets

Secrets are injected into your functions using environment variables. By defining variables in the provider section of the `serverless.yml` you add them to the environment of the deployed function. From there, you can reference them in your functions as well.

So you would add something like:
```yml
provider:
  environment:
    A_VARIABLE: ${env:A_VARIABLE}
```
to your `serverless.yml`, and then you can add `A_VARIABLE` to your GitLab Ci variables and it will get picked up and deployed with your function.

For local development, we suggest installing something like [dotenv](https://www.npmjs.com/package/dotenv) to manage environment variables.

### Setting Up AWS

1. Create AWS credentials including the following IAM policies: `AWSLambdaFullAccess`, `AmazonAPIGatewayAdministrator` and `AWSCloudFormationFullAccess`.
1. Set the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` variables in the GitLab CI/CD settings. `Settings > CI/CD > Variables`.

### Accessing Page

To view your page go to `Settings > Pages` and click on the given link.

## Development

### Running Locally

Install dependencies with:

```sh
npm install
```

Run backend server with:

```sh
npm start
```

This runs the serverless function locally using `serverless-offline` plugin.

Run frontend with:

```sh
npm run pages
```

The frontend should be available at `http://localhost:8080`

### Running Tests
```sh
npm test
```

#### Unit Tests

For the serverless backend, unit tests live with the src files as `srcFile.test.js`. The unit tests use the `serverless-jest-plugin` and lambda wrapper to simulate events to the functions and validate their outputs.

#### Feature Tests

Feature tests live in the folder `featureTests`. Those tests allow us to spin up serverless offline as a service and make requests against it and validate the results of those requests.

Feature tests double as post deploy tests when the environment variable `STACK_JSON_FILE` is specified with the path to the file generated on deployment (`stack.json`), see in `gitlab-ci.yml`.

A typical feature test will look something like:

```javascript
// This helper provides access to the serverless process and an axios instance
// to make requests against the running service.
const { serverlessProcess, serverlessService } = require('./helper.js')

describe('some_function', () => {
    beforeAll(async () => {
        // serverlessProcess.start starts serverless offline in a child process
        await serverlessProcess.start()
    })

    afterAll(() => {
        // serverlessProcess.stop kills the child process at the end of the test
        serverlessProcess.stop()
    })

    it('responds to a request', async () => {
        // The axios instance has the base url and port already, so you just have
        // to provide a route and any paramters or headers. See the axios project
        // for details.
        let response = await serverlessService.get('/some_route?param=here')

        expect(response.data.info).toEqual('amazing')
    })
});
```

## Additional information

### Getting the Endpoint URL

This project is setup with the `serverless-stack-output plugin` which is configured to output a JSON file to `./stack.json`. See [this github repo](https://github.com/sbstjn/serverless-stack-output) for more details.

