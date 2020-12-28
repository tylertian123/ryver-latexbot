# LaTeX Bot Deployment Guide

So you want to install LaTeX bot for your own organization? Well this is how.

- [Background](#background)
- [Basic Setup](#basic-setup)
  - [Data Storage](#data-storage)
  - [Configuration](#configuration)
  - [Credentials](#credentials)
- [Optional Features](#optional-features)
  - [Server](#server)
  - [Google Calendar Integration](#google-calendar-integration)
  - [The Blue Alliance (TBA) Integration](#the-blue-alliance-tba-integration)
  - [GitHub Integration](#github-integration)
- [Building](#building)
- [Deploying](#deploying)
- [Deploying on a single machine](#deploying-on-a-single-machine)
- [Environment Variables](#environment-variables)

## Background

LaTeX Bot runs as a stack of custom docker containers. We store these as a `docker-compose` file, since our installation runs on a docker swarm.
If you use Kubernetes, you may be able to use the new `kubernetes` orchestrator for `docker stack deploy`. The rest of this guide will assume you
are using a docker swarm to host LaTeX Bot. It is possible to use a single dedicated machine instead, see the end of the guide for more on this approach.

On the Ryver side, LaTeX Bot effectively is its own Ryver client, controlling its own user. In our setup, this user is named `latexbot`. In order for all functionality
to work, you must have an Org Admin level account setup which the bot will use to send messages and generally interact. This account should _only_ be for the bot (although
it is perfectly fine to login to the account while the bot is running to change profiles for example, although if you send any messages it might get a little confusing!)

## Basic Setup

### Data Storage

LaTeX Bot needs persistent data storage. It will store all of its data as JSON files under its Data Directory.
The location of this directory is set through the env var `LATEXBOT_DATA_DIR`, which **must** be set.

If you're using Docker, you can use a Docker volume for this purpose. See `docker-compose.yml` for an example.

### Configuration

Most of LaTeX Bot's nonessential configuration is located in the main configuration JSON, at `$LATEXBOT_DATA_DIR/config.json`.
You can also edit this through the `importConfig` and `exportConfig` commands once the bot is set up. For documentation on the configuration file format, see `usage_guide.md`.

Separate to the main configuration file, you will probably need to do some tweaking to the main `docker-compose` file to get it to run on your swarm. We currently push
to a private registry, and unless you build the container on every single node in your swarm and tag it appropriately, you will need to to change the registry to your own private
one; as the credentials for accessing Google Calendar are embedded in the container.

### Credentials

LaTeX Bot needs a set of credentials to log into your organization.
There are two ways of providing credentials; the first is to set `LATEXBOT_CREDENTIALS_JSON` to the path of a JSON file with the following format:

```json5
{
    "organization": "Your organization name, e.g. arctos6135",
    "username": "The username of the account used by LaTeX Bot, e.g. latexbot",
    "password": "The password of the account used by LaTeX Bot"
}
```

This is the preferred method, especially if you're using Docker.
It's convenient to store the credentials JSON in a Docker secret, and then set `LATEXBOT_CREDENTIALS_JSON` to the secret mountpoint at `/run/secrets/<name>` (see `docker-compose.yml` for an example).
If you're deploying with compose (as opposed to swarm), the secret must be a file and not external (see `docker-compose.dev.yml`).

The other method is to use the following environment variables:

- `LATEXBOT_ORG` - Your organization name
- `LATEXBOT_USER` - The username for the account
- `LATEXBOT_PASSWORD` - The password for the account

These may be convenient for testing purposes, and if set, will override `LATEXBOT_CREDENTIALS_JSON`.

Please note that LaTeX Bot *does not* support signing in with a Custom Integration (i.e. a full user account has to be created for it).
This is due to `pyryver`'s lack of support for realtime sessions for Custom Integrations.

## Optional Features

### Server

LaTeX Bot can host a server that provides diagnostic information, an analytics dashboard (if enabled). The server **must** be enabled for GitHub integrations to work.

To enable the server, set `LATEXBOT_SERVER` to 1 to host the server on port 80. Or, set `LATEXBOT_SERVER_PORT` to a port number. Only one of the variables needs to be set.

The server allows for actions such as reading the configuration files and analytics data, and sending messages. Basic auth is needed to access some functions.
There are 3 sets of credentials, `read`, `write` and `admin`, with passwords configured with `LATEXBOT_SERVER_AUTH_READ`, `LATEXBOT_SERVER_AUTH_WRITE`, and `LATEXBOT_SERVER_AUTH_READ` respectively.
If a password is unset, the login will be disabled.

### Google Calendar Integration

For Google Calendar Integration to work, you will need to create a Google Cloud project and grant it access to the Google Calendar API.
Then, create a service account (skip all the optional steps during creation), and create JSON credentials for it. Save these credentials somewhere.

Set `LATEXBOT_CALENDAR_CREDENTIALS` to the path of the credentials JSON. This defaults to `calendar_credentials.json` if unset, although most of the time it's probably not what you want.

If you're deploying with Docker, it's convenient to store these as a secret. See [Credentials](#credentials) for more details.

Make sure that you share the calendar to use with the service account.
After this, go to the settings for the calendar, and copy the calendar ID at the bottom.
Put this calendar ID in the configuration JSON as the `"googleCalendarId"` field, and you're done!

### The Blue Alliance (TBA) Integration

To set up TBA integration, you will need to supply LaTeX Bot with a read token.
Without this token, LaTeX Bot will not be able to query TBA.
You can generate a Read API Key in your [Account Dashboard](https://www.thebluealliance.com/account).
Copy the value of the key, and set it as the `LATEXBOT_TBA_KEY` env var.

Additionally, if you wish to see your team number highlighted in the generated ranking tables, you need to set the `"frcTeam"` field in the JSON config.
When this is set, LaTeX Bot will highlight rows containing info about your team in the output of `districtRankings`, `eventRankings` and other relevant commands.

### GitHub Integration

Currently, GitHub integration uses webhooks. This requires the server to be enabled (see [Server](#server)).
You can either use an organization webhook or a repository webhook, although an org webhook is preferred if you have an organization, since LaTeX Bot has multi-repository support.
Follow [this guide](https://developer.github.com/webhooks/creating/) to set up a webhook for LaTeX Bot.

By default, LaTeX Bot will host the server on port 80, and can be changed by the `LATEXBOT_SERVER_PORT` env var (note this affects the container, modify the compose file to change the port on the host).
See [Server](#server) for more info. The endpoint for the webhook is at `/github`.
The payload must be set as `application/json` (**not** `application/x-www-form-urlencoded`).

LaTeX Bot also supports optional webhook secrets. When the `LATEXBOT_GH_HOOK_SECRET` env var is set, LaTeX Bot will use it to verify the signatures on all incoming GitHub webhooks, returning a 401 Unauthorized response if the signature is wrong or missing.

When setting up the webhook, you can simply select "Send me **everything**". However, only these events will be processed (in brackets is the API event type):

- Check runs (`check_run`)
- Commit comments (`commit_comment`)
- Branch or tag creation and deletion (`push`)
- Forks (`fork`)
- Issue comments (`issue_comment`)
- Issues (creation, deletion, closing, etc) (`issues`)
- Organizations (new members, etc) (`organization`)
- Repo visibility changes (`repository`)
- Pull requests (creation, deletion, merging, closing, etc) (`pull_request`)
- Pull request reviews (`pull_request_review`)
- Pull request review comments (`pull_request_review_comment`)
- Pushes (`push`)
- Stars (`star`)

The `"ghUpdatesChat"` field in the config must be set for GitHub updates, and the `"ghIssuesChat"` field must be set for integration with Ryver Tasks.
Please note that the chat for `"ghIssuesChat"` must have a board-type (that is, with categories, and not a list) task board, or no task board (in which case it will be created).

Additionally, in order for assignment/unassignment to work, the assigned GitHub user's username must be present in `"ghUsersMap"` in the config.

## Building

Once you have completed the above steps, use `docker-compose build` and `docker-compose push` to build and push your images to the registry you named in the above section.
Make sure the`calendar_credentials.json` file is present for this step if you're building it into the container and not loading it via a secret and  `LATEXBOT_CALENDAR_CRED_FILE`.

Do note that the `tex-slave` image, used to render all LaTeX, is rather large, usually around a gigabyte in size.

## Deploying

Before deploying, make sure that Ryver credentials are provided through either environment variables or a JSON file. See [Credentials](#credentials) for more info.

Additional environment variables can be found below at [Environment Variables](#environment-variables).

If on the terminal, use `docker stack deploy --compose-file docker-compose.yml <some_name>` to deploy. See the documentation for that command for more information.

## Deploying on a single machine

If you have a single dedicated machine (for example an el cheapo VPS, raspberry pi, etc.) you may find it easier to deploy without swarm mode. In this case, the requirements are simply to
have a functioning installation of Docker.

To setup LaTeX Bot in this mode, follow the [Configuration](#configuration) and [Building](#building) steps, except don't run `docker-compose push` or setup/change the registry.

Once you have done this, set the environment variables as explained in [Deploying](deploying) and simply run `docker-compose up -d` to create and start the necessary containers.

## Environment Variables

Here is a complete list of all the environment variables that affect LaTeX Bot. Some of them are very important. Most of these are optional unless marked otherwise.

- `LATEXBOT_DATA_DIR` (**Required**) - A path to the directory where LaTeX Bot will store its data.
- `LATEXBOT_CREDENTIALS_JSON` (**Required unless the three below are set**) - A path to a JSON containing Ryver login credentials; see [Credentials](#credentials).
- `LATEXBOT_ORG` (**Required unless `LATEXBOT_CREDENTIALS_JSON` is set**) - The organization name.
- `LATEXBOT_USER` (**Required unless `LATEXBOT_CREDENTIALS_JSON` is set**) - The username of the bot account.
- `LATEXBOT_PASSWORD` (**Required unless `LATEXBOT_CREDENTIALS_JSON` is set**) - The bot account's password.
- `LATEXBOT_MAINTAINER_ID` - The user ID of the bot's Maintainer. This user is given access to all commands among other privileges.
- `LATEXBOT_CALENDAR_CREDENTIALS` - The path to the file containing the service account credentials for the calendar; see [Setting Up Google Calendar Integration](#setting-up-google-calendar-integration).
- `LATEXBOT_ANALYTICS` - Set to 1 to enable analytics.
- `LATEXBOT_SERVER` - Set to 1 to enable the server (by default hosted on port 80). Does not need to be set if the port is already specified.
- `LATEXBOT_SERVER_PORT` - The port to host the web server on.
- `LATEXBOT_SERVER_AUTH_READ` - The password for the "read" account in the web server. See [Server](#server).
- `LATEXBOT_SERVER_AUTH_WRITE` - The password for the "write" account in the web server. See [Server](#server).
- `LATEXBOT_SERVER_AUTH_ADMIN` - The password for the "admin" account in the web server. See [Server](#server).
- `LATEXBOT_GH_HOOK_SECRET` - The HMAC secret key for incoming webhook messages from GitHub.
- `LATEXBOT_TBA_KEY` - The key used to access the The Blue Alliance API.
- `LATEXBOT_DEBUG` - Set to 1 for debug mode.
