# LaTeX Bot Deployment Guide

So you want to install LaTeX bot for your own organization? Well this is how.

## Background

LaTeX Bot runs as a stack of custom docker containers. We store these as a `docker-compose` file, since our installation runs on a docker swarm.
If you use Kubernetes, you may be able to use the new `kubernetes` orchestrator for `docker stack deploy`. The rest of this guide will assume you
are using a docker swarm to host LaTeX Bot. It is possible to use a single dedicated machine instead, see the end of the guide for more on this approach.

On the Ryver side, LaTeX Bot effectively is its own Ryver client, controlling its own user. In our setup, this user is named `latexbot`. In order for all functionality
to work, you must have an Org Admin level account setup which the bot will use to send messages and generally interact. This account should _only_ be for the bot (although
it is perfectly fine to login to the account while the bot is running to change profiles for example, although if you send any messages it might get a little confusing!)

## Configuration

Separate to the main configuration file, you will probably need to do some tweaking to the main `docker-compose` file to get it to run on your swarm. We currently push 
to a private registry, and unless you build the container on every single node in your swarm and tag it appropriately, you will need to to change the registry to your own private
one; as the credentials for accessing Google Calendar are embedded in the container.

### Setting Up Google Calendar Integration

For Google Calendar Integration to work, you will need to create a Google Cloud project and grant it access to the Google Calendar API.
Then, create a service account (skip all the optional steps during creation), and create JSON credentials for it. 
Save these in the root of this repository as `calendar_credentials.json`.

Make sure that you share the calendar to use with the service account.
After this, go to the settings for the calendar, and copy the calendar ID at the bottom. 
Put this calendar ID in the configuration JSON as the `"googleCalendarId"` field, and you're done!

### Setting Up GitHub Integration

Currently, GitHub integration uses webhooks.
You can either use an organization webhook or a repository webhook, although an org webhook is preferred if you have an organization.
Follow [this guide](https://developer.github.com/webhooks/creating/) to set up a webhook for LaTeX Bot.

By default, LaTeX Bot will host the server on port 80.
This can be changed using the `LATEXBOT_SERVER_PORT` env var.
The endpoint for the webhook is at `/github`. 

LaTeX Bot also supports optional webhook secrets.
When the `LATEXBOT_GH_HOOK_SECRET` env var is set, LaTeX Bot will use it to verify the signatures on all incoming GitHub webhooks, and returning a 401 Unauthorized response if the signature is wrong or missing.

When setting up the webhook, you can simply select "Send me **everything**". 
However, only these events will be processed (in brackets is the API event type):
- Check runs (`check_run`)
- Commit comments (`commit_comment`)
- Branch or tag creation (`push`)
- Branch or tag deletion (`push`)
- Forks (`fork`)
- Issue comments (`issue_comment`)
- Issues (`issues`)
- Organizations (`organization`)
- Visibility changes (`repository`)
- Pull requests (`pull_request`)
- Pull request reviews (`pull_request_review`)
- Pull request review comments (`pull_request_review_comment`)
- Pushes (`push`)
- Stars (`star`)

## Building

Once you have completed the above steps, use `docker-compose build` and `docker-compose push` to build and push your images to the registry you named in the above section. Make sure the
`calendar_credentials.json` file is present for this step.

Do note that the `tex-slave` image, used to render all LaTeX is rather large, usually around a gigabyte in size.

## Deploying

If you use a management UI for your swarm which does not allow you to set environment variables, such as Swarmpit, you should change the `LATEXBOT_ORG`, `LATEXBOT_USER` and `LATEXBOT_PASS` variables
in the `docker-compose.yml` file to appropriate values (see below).

If you are deploying directly from the terminal, first set the following environment variables:

- `LATEXBOT_ORG`: your organization's name, as seen in the URL
- `LATEXBOT_USER`: the username of the account set aside for LaTeX Bot
- `LATEXBOT_PASS`: the password of the account set aside for LaTeX Bot

If you are using a management UI that _does_ support environment variables, set them in whatever way it uses to the same values, and deploy the `docker-compose` file that you modified earlier.

If on the terminal, use `docker stack deploy --compose-file docker-compose.yml <some_name>` to deploy. See the documentation for that command for more information. 

## Deploying on a single machine

If you have a single dedicated machine (for example an el cheapo VPS, raspberry pi, etc.) you may find it easier to deploy without swarm mode. In this case, the requirements are simply to 
have a functioning installation of Docker.

To setup LaTeX Bot in this mode, follow the [Configuration](configuration) and [Building](building) steps, except don't run `docker-compose push` or setup/change the registry.

Once you have done this, set the environment variables as explained in [Deploying](deploying) and simply run `docker-compose up -d` to create and start the necessary containers.
