galatea-hal
=============

## Overview
Galatea Hal is our own natural language enabled internal bot for common tasks.   
Hal is hosted on BeepBoop. Visit [Beep Boop](https://beepboophq.com/docs/article/overview) to get the scoop on the the Beep Boop hosting platform. 

## Development
I hear you want to contribute to hal.  Awesome.  Here are some guidelines.

### Assumptions

We assume you understand the following:
- How to develop in Python3 (we have a slack channel for this)
- How to interact with GitHub. 
- What docker is
- How REST APIs work. In fact, you should get a copy of postman from the chrome store
- The slack realtime API:  https://api.slack.com/rtm  
- How BeeBoop works: https://beepboophq.com/docs 
- How Wit.ai works: https://wit.ai/ .  Specifically the REST API: https://wit.ai/docs/http/20160526#get--message-link

### Initial set up
Here are some initial set up steps
- Install latest version of Python 3. https://www.python.org/downloads/ Note: this is an upgrade from previous versions, which ran Python 2.7
- Add the python and python\scripts directories to your path (e.g. C:\"Program Files"\Python35 and C:\"Program Files"\Python35\Scripts)
- Install your favorite python editor.  I like community edition of pycharm:  https://www.jetbrains.com/pycharm/download/#section=windows)
- Get postman extension to chrome:  https://chrome.google.com/webstore/detail/postman/fhbjgbiflinjbdggehcddcbncdddomop?hl=en .  This should allow you to make REST calls to wit or slack.  It's a useful way to test.
- Sign up for github and ask Raj to add you as a collaborator
- Run through the github set up guide:  https://help.github.com/articles/set-up-git/
- Fork this repository
- Create a bot for yourself to test hal:  https://galaslack.slack.com/apps/manage/A0F7YS25R-bots .  This bot should be called test-hal-<your name> (e.g. test-hal-raj).  This will ensure that your changes don't break production hal.  Note: be polite and disable your bot when you are not using it.  You'll need to keep track of your bot's slack token when you go to test your bot.
- Go to [The Google Developer Console](https://console.developers.google.com) and create a new project.
- Within this project, create a new client ID, of type 'Web Application'
- Make sure that you set one of the authorized redirect URI's to a public web URI, port 5555, that you have access too, i.e. http://place.sample.com:5555
- Under overview, enable all the api's you'll be using. Currently, that is Gmail and Google Drive.
- Talk to Raj so we can figure out how best to share the wit app.  Wit used to have a fork feature but not sure that is there anymore.
- If you have problems with this setup, or during dev, don't hesitate to contact John Casey with questions

### Dev Process
- Make your changes
- Test your changes
- Send Raj a pull request

### Code Organization
If you want to add or change an event that the bot responds (e.g. when the bot is mentioned, when the bot joins a channel, when a user types a message, etc.), you can modify the `_handle_by_type` method in `event_handler.py`.

The `slack_clients.py` module provides a facade of two different Slack API clients which can be enriched to access data from Slack that is needed by your Bot:
1. [slackclient](https://github.com/slackhq/python-slackclient) - Realtime Messaging (RTM) API to Slack via a websocket connection.
2. [slacker](https://github.com/os/slacker) - Web API to Slack via RESTful methods.

The `slack_bot.py` module implements and interface that is needed to run a multi-team bot using the Beep Boop Resource API client, by implementing an interface that includes `start()` and `stop()` methods and a function that spawns new instances of your bot: `spawn_bot`.  It is the main run loop of your bot instance that will listen to a particular Slack team's RTM events, and dispatch them to the `event_handler`.

The `intenthandler` package contains the code that handles intents returned by wit.ai.  Make sure to read the REST API link under assumptions so that you understand exactly what is being returned (intent isn't the only entity).  If you add a new intent handler, you'll need to register it in the `intents` dict in the RtmEventHandler class of `event_handler.py`.  The key must be equal to the intent string that will be returned by wit.

##### State
States are currently being preserved in state objects (see state.py). In particular, if you would like to introduce a new type of state, particularly a new type of conversation, please extend State, or ConversationState
##### Threads
If you need a thread, please implement it in threads.py.

In addition, we are also using a threadpool to execute tasks, so Hal can be internally asynchronous and non-blocking
##### OAuth 2.0
OAuth is a complex protocol, and you would be well served reading the many guides online, as well as the Google specific documentation. However, there are a number of small points that are worth mentioning here.
- When implementing a new method that requires a user authenticate, use the process found in google_helpers.py's send_email function. Generate a new uuid, then try and get the credentials for the user. If the credentials cannot be found,
create a WaitState based on that uuid, and return it. The RtmEventHandler will take charge of this WaitState, and will resume the method call when authentication is completed.
- probably is more to say...

##### cryptography.fernet
We are useing Fernet for symmetrical encryption to encrypt our state as we pass through google OAuth.
##### fuzzywuzzy
Fuzzywuzzy is a fuzzy string matching library, which we are using for google drive lookups to account for slight misspellings of actual file names.


### Testing locally (on windows)

To start your local version of hal, run the following steps from a command prompt:
- cd to your project root folder (i.e. where you have requirements.txt)
- pip install -r requirements.txt (you should only have to do this when you run the bot for the first time on your computer OR the requirements file changes)
- set SLACK_TOKEN=[YOUR TEST HAL BOT's SLACK TOKEN] (you should only have to set this once per command prompt instance)
- set WIT_ACCESS_TOKEN=[YOUR WIT ACCESS TOKEN] (you should only have to set this once per command prompt instance)
- set GOOGLE_CLIENT_ID=[YOUR CLIENT ID] (This is the id of the client you created during set-up)
- set GOOGLE_CLIENT_SECRET=[YOUR CLIENT SECRET] (This is the id of the client you created during set-up)
- set CALLBACK_URI=[YOUR PUBLIC URI]:5555 (This is where Google sends the oauth callback, must match the callback uri specified above)
- set FERNET_KEY=[encryption key] (This is the key you got when you created the encrypted oauth credentials. It is also used to encrypt and decrypt state as sent to Google)
- set BEEPBOOP_TOKEN=[whatever you want] (There is a check in the code which requires a beepboop token, but it is only useful in prod)
- set DEFAULT_USER=['hal' in prod, your real name in slack in testing](defines the default user for unauthenticated google queries)
- python ./bot/app.py

Things are looking good if the console prints something like:

	Connected <your bot name> to <your slack team> team at https://<your slack team>.slack.com.

If you want change the logging level, also `set LOG_LEVEL=<your level>`

Ctrl-c will no longer kill the bot, as it is now multi-threaded.

If you would like to set environment variables persistently on Windows, you can go to System Properties->Advanced->Environment Variables. Any changes you make here will be updated in any new cmd instances.

### Deploying to prod
Changes pushed to the remote master branch will automatically deploy a new version of hal

## License

See the [LICENSE](LICENSE.txt) file for license rights and limitations (MIT).
