let username = "",
    roomName = "",
    isInGame = false,
    socket = io.connect(window.location.href);

// OnLoginClicked function
$("#noname_form").on("submit", function (e) {
    e.preventDefault();
    let requested_username = $("input.username").val();
    if (requested_username.length > 0)
        socket.emit("register_client", {username: requested_username}, registerUsername);
});

// Register username
function registerUsername(confirmed_username, confirmed_roomName, otherPlayers, minPlayers, is_game_starting, msgJson){
    if (confirmed_roomName) {
        username = confirmed_username;
        roomName = confirmed_roomName;
        isInGame = true;
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
                default:
                    console.error("Unexpected action received on players_update");
            }
            break;

        case "new_game":
            announceGameStatus("starting")
            break;

        case "new_round":
            runRound(msg)
            break;

        case "round_stats":
            announceRoundStats(msg)
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
            if (player_name == username) isInGame = false;
            let player_label = $(`label#player_tag_${player_name}`)
            if (player_label.length > 0)
                player_label.remove();

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
        questionWrapper =  $("div#question-wrapper"),
        optionsWrapper =  $("div#options-wrapper");
    gameInfoWrapper.empty();
    gameInfoWrapper.append(
        `<h2 class="text-center" id="game-info-wrapper" style="color: #ccc">
            Round ${roundInfo["round"]}
        </h2>`
    );

    questionWrapper.empty()
    questionWrapper.append(
        `
        <blockquote class="blockquote text-center">
          <p class="mb-0">${roundInfo["question"]}</p>
        </blockquote>
        `
    );

    optionsWrapper.empty()
    optionsWrapper.append(
        `
        <div class="container">
            <button type="button" class="option-btn btn btn-light" id="option-button-0" name="${roundInfo["options"][0]}"
                value="${roundInfo["round_answer_key"]}" onclick="selectRoundOption(this)" ${isInGame ? "" : "disabled"}>
                    ${roundInfo["options"][0]}
            </button>
        </div>
        <div class="container">
            <button type="button" class="option-btn btn btn-light" id="option-button-1" name="${roundInfo["options"][1]}"
                value="${roundInfo["round_answer_key"]}"  onclick="selectRoundOption(this)" ${isInGame ? "" : "disabled"}>
                    ${roundInfo["options"][1]}
            </button>
        </div>
        <div class="container">
            <button type="button" class="option-btn btn btn-light" id="option-button-2" name="${roundInfo["options"][2]}"
                value="${roundInfo["round_answer_key"]}" onclick="selectRoundOption(this)" ${isInGame ? "" : "disabled"}>
                    ${roundInfo["options"][2]}
            </button>
        </div>
        `
    );

    runTimer(roundInfo["timer"], function () {
        $(`button.option-btn`).prop("disabled", true);
    });
}

function announceRoundStats(roundStats) {
    let gameInfoWrapper = $("div#game-info-wrapper"),
        optionsWrapper =  $("div#options-wrapper"),
        gameInfoStr = roundStats["players_in_game"] <= 1
            ?
                "Game Over"
            :
                `<div class="spinner-grow" id="spinner-waiting" role="status"> </div> Round ${roundStats["round"]}`;
    gameInfoWrapper.empty();
    gameInfoWrapper.append(
        `<h2 class="text-center" id="game-info-wrapper" style="color: #ccc">
            ${gameInfoStr}
        </h2>`
    );

    optionsWrapper.empty()
    optionsWrapper.append(
        `
        <div class="container" style="height: 0.1rem">
        </div>
        
        <div class="progress position-relative option-stat-bar">
            <div class="container position-absolute" >
                <p style="line-height: 2.45rem; font-size: 1rem; color: #212529">${roundStats["options"][0]}</p>
            </div>
            <div class="progress-bar bg-success" role="progressbar" 
                style="width: ${roundStats["stats"][roundStats["options"][0]] * 100}%; 
                    background-color: ${roundStats["options"][0] == roundStats["correct_answer"] ? "#9dff9d" : "lightgray"} !important;" 
                aria-valuenow="${roundStats["stats"][roundStats["options"][0]] * 100}" 
                aria-valuemin="0" aria-valuemax="100">              
            </div>
        </div>
        
        <div class="progress position-relative option-stat-bar">
            <div class="container position-absolute" >
                <p style="line-height: 2.45rem; font-size: 1rem; color: #212529">${roundStats["options"][1]}</p>
            </div>
            <div class="progress-bar bg-success" role="progressbar" 
                style="width: ${roundStats["stats"][roundStats["options"][1]] * 100}%; 
                    background-color: ${roundStats["options"][1] == roundStats["correct_answer"] ? "#9dff9d" : "lightgray"} !important;" 
                aria-valuenow="${roundStats["stats"][roundStats["options"][1]] * 100}" 
                aria-valuemin="0" aria-valuemax="100">              
            </div>
        </div>
        
        <div class="progress position-relative option-stat-bar">
            <div class="container position-absolute" >
                <p style="line-height: 2.45rem; font-size: 1rem; color: #212529">${roundStats["options"][2]}</p>
            </div>
            <div class="progress-bar bg-success" role="progressbar" 
                style="width: ${roundStats["stats"][roundStats["options"][2]] * 100}%; 
                    background-color: ${roundStats["options"][2] == roundStats["correct_answer"] ? "#9dff9d" : "lightgray"} !important;" 
                aria-valuenow="${roundStats["stats"][roundStats["options"][2]] * 100}" 
                aria-valuemin="0" aria-valuemax="100">              
            </div>
        </div>
        `
    );
}

function selectRoundOption(btnInfo) {
    reportRoundAnswer(btnInfo.name, btnInfo.value)
    // Block on option to change the decision
    $(`button#${btnInfo.id}`).css("background-color", "#007BFF").css("color", "white");
    $(`button.option-btn`).prop("disabled", true);
}

function reportRoundAnswer(answer, round_answer_key) {
    socket.emit("report_round_answer", {
        room_name: roomName,
        username: username,
        answer: answer,
        round_answer_key: round_answer_key,
    });
}

function runTimer(time, callback) {
    let initialOffset = "188";
    let i = 1;

    // Initialization
    $("h2.timer_text").text(time);
    $(".timer_text").css("color", "black");
    $(".circle_animation").css("stroke", "#6fdb6f");
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
                // Return timer arc to the initial position
                $(".circle_animation").css("stroke-dashoffset", initialOffset);
                // Do a callback if any
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