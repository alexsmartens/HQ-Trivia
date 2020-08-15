# HQ-Trivia II Game
## Heroku Flask-SocketIO Redis Eventlet Gunicorn

Check out [this game](https://hq-trivia2.herokuapp.com) on Heroku.

Check out [game architecture presentation](https://prezi.com/view/KFCbpuFDe1zv89X0mXPq/) on Prezi.

### UI
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/0_screenshot.png)

### Some game insights
- type in your favourite nickname and press "Log in" to start playing;
- a player with any name can join a game as long as there is no player with the same name already exists in this gaming room;
- game starts when at least 2 players joined;
- there is a _10 sec_ waiting time for other players to join the game after the minimum number of players have joined the game;
- the first round starts after the initial _10 sec_  waiting time;
- the game ends when there is only one player in the game (or none players if everyone lost);
- each game runs in a separate gaming room. When a game or multiple games is/are already running then a new gaming room is created.

### Presentation: Game Architecture

#### Intro
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/1_intro.png)

#### Requirements & Outline
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/2_requirements_outline.png)

#### Wireflow
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/3_wireflow.png)

#### Server-Client Communication for Real-Time Browser Game
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/4_server-client_communication.png)

#### Stack
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/5_stack.png)

#### How to scale?
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/6_scaling.png)

#### UML Class Diagram
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/7_uml_diagram.png)

#### Flowchart
![alt text](https://github.com/alexsmartens/HQ-Trivia/blob/master/documentation/8_flowchart.png)

### Running locally

1) Download/clone the project.
2) Navigate to the project directory.
3) Install all the dependencies from `requirements.txt`.
4) Launch the server with `gunicorn --worker-class eventlet -w 1 game_server:app`.
5) Open `http://127.0.0.1:8000/` in your favourite browser and start gaming.

### Deploying on Heroku with Git
Refer to [deploying with Git](https://devcenter.heroku.com/articles/git).
