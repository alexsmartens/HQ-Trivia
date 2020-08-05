let username = "",
    roomName = "",
    socket = io.connect(window.location.href)

// OnLoginClicked function
$("#noname_form").on("submit", function (e) {
    e.preventDefault()
    username = $("input.username").val();
    if (username.length > 0)
        socket.emit("register_client", {username: username}, registerUsername);
});

// Register username
function registerUsername(username, roomName, otherPlayers, minPlayers, is_game_starting, msgJson){
    if (roomName) {
        $("[id^=noname]").prop("disabled", true);
        $(".label_players").css("color", "black");
        if (is_game_starting)
            announceGameStatus("starting", minPlayers)
        else
            announceGameStatus("waiting", minPlayers);

        addPlayers(otherPlayers);
        updatePlayer("add_me", username);
    } else {
        informUser(JSON.parse(msgJson));
    };
}

// Receive a message
socket.on("message", function (msg) {
    informUser (msg);
});


function informUser (msg) {
    switch (msg["type"]) {
        case "info":
            console.log(msg["msg"]);
            break;

        case "warning":
            console.warn(msg["msg"]);
            break;

        case "players_update":
            switch (msg["action"]) {
                case "joined":
                    if (msg["username"] == username)
                        {}
                    else
                        updatePlayer("add", msg["username"]);
                    break;
                case "left":
                    updatePlayer("remove", msg["username"]);
                    break;
                case "remove":
                    $(`label#player_tag_${player_name}`).remove();
                    break;
                default:
                    console.error("Unexpected action received on players_update");
            }
            break;

        case "new_game":
            announceGameStatus("starting")
            break;

        case "new_round":
            console.log("* Start round")
            console.log(msg)
            runRound(msg)
            break;

        default:
            console.error("Not expected msg type");
    }
}

function addPlayers(players) {
    Object.keys(players).forEach(function(player_name) {
        updatePlayer("add", player_name);
    });
}

function updatePlayer(command, player_name) {
    switch (command) {
        case "add":
            $("div.player_wrapper").append(
                `<label class="player_tag" id="player_tag_${player_name}">${player_name}</label>`
            );
            break;
        case "add_me":
            $("div.player_wrapper").append(
                `<label class="me_player_tag" id="player_tag_${player_name}">${player_name}</label>`
            );
            break;
        case "remove":
            let player_left_tag = $("div#spinner-starting");
            if (player_left_tag.length > 0) {
                $(`label#player_tag_${player_name}`).remove()
            }
            break;
        default:
            console.error("Not expected add player command");
    }
}

function announceGameStatus(status, minPlayers){
    let gameInfoWrapper = $("div#game-info-wrapper");
    switch (status) {
        case "waiting":
            gameInfoWrapper.empty();
            let waiting_str = "Waiting for more players to join...";
            if (minPlayers)
                waiting_str = `Game will Start when ${minPlayers} Players Join`
            gameInfoWrapper.append(
                `<h2 class="text-center" id="game-info-wrapper" style="color: #ccc">
                    <div class="spinner-grow" id="spinner-waiting" role="status"> </div>
                    ${waiting_str}
                </h2>`
            );
            break;
        case "starting":
            if ($("div#spinner-starting").length == 0){
                // Exclude of possibility of doing this twice (when the last user joined and on the game announcement)
                gameInfoWrapper.empty();
                gameInfoWrapper.append(
                    `<h2 class="text-center" id="game-info-wrapper" style="color: #DC3545">
                        <div class="spinner-grow text-danger" id="spinner-starting" role="status"> </div>
                        Get Ready! 
                    </h2>`
                );
            }
            break;
        default:
            console.error("Not expected game announce command");
    }
}

function runRound(roundInfo){
    let gameInfoWrapper = $("div#game-info-wrapper"),
        roundWrapper =  $("div#round-wrapper");
    gameInfoWrapper.empty();
    gameInfoWrapper.append(
        `<h2 class="text-center" id="game-info-wrapper" style="color: #ccc">
            Round ${roundInfo["round"]}
        </h2>`
    );

    roundWrapper.empty()
    roundWrapper.append(
        `
        <blockquote class="blockquote text-center">
          <p class="mb-0">${roundInfo["question"]}</p>
        </blockquote>
        <div class="container">
            <button type="button" class="option-btn btn btn-light" id="option-button-0" name="${roundInfo["options"][0]}"
                value="${roundInfo["pub_answer_key"]}" onclick="selectRoundOption(this)">${roundInfo["options"][0]}</button>
        </div>
        <div class="container">
            <button type="button" class="option-btn btn btn-light" id="option-button-1" name="${roundInfo["options"][1]}"
                value="${roundInfo["pub_answer_key"]}"  onclick="selectRoundOption(this)">${roundInfo["options"][1]}</button>
        </div>
        <div class="container">
            <button type="button" class="option-btn btn btn-light" id="option-button-2" name="${roundInfo["options"][2]}"
                value="${roundInfo["pub_answer_key"]}" onclick="selectRoundOption(this)">${roundInfo["options"][2]}</button>
        </div>
        `
    );

    runTimer(roundInfo["timer"], function () {
        $(`button.option-btn`).prop("disabled", true);
    });
}

function selectRoundOption(btnInfo) {
    reportRoundAnswer(btnInfo.name, btnInfo.value)
    // Block on option to change the decision
    $(`button#${btnInfo.id}`).css("background-color", "#007BFF").css("color", "white");
    $(`button.option-btn`).prop("disabled", true);
}

function reportRoundAnswer(answer, pub_answer_key) {
    socket.emit("report_round_answer", {
        username: username,
        answer: answer,
        pub_answer_key: pub_answer_key,
    });
}

function runTimer(time, callback) {
    let initialOffset = "188";
    let i = 1;

    // Initialization
    $("h2.timer_text").text(time);
    $(".timer_text").css("color", "black");
    $(".circle_animation").css("stroke", "#6fdb6f");
    $(".circle_animation").css("stroke-dashoffset", initialOffset);
    setTimeout(() => {
        $(".circle_animation").css("stroke-dashoffset", initialOffset - (1 * (initialOffset / time)));
    })

    // Timer
    let interval = setInterval(function () {
        // Update text
        $(".timer_text").text(time - i);
        // Animation control
        switch (time - i) {
            case 0:
                // Stop
                $(".timer_text").css("color", "white");
                $(".circle_animation").css("stroke", "white");
                clearInterval(interval);
                if (callback) callback()
                // Stop circle animation
                return;
                break;
            case 2:
                // Red color
                $(".circle_animation").css("stroke", "red");
                break;
            case Math.floor(time / 2):
                $(".circle_animation").css("stroke", "orange");
                break;
        }
        // Update the circle
        $(".circle_animation").css("stroke-dashoffset", initialOffset - ((i + 1) * (initialOffset / time)));
        i++;
    }, 1000);
}