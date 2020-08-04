let username = "",
    roomName = "",
    socket = io.connect(window.location.href)

// OnLoginClicked function
$("#noname_form").on("submit", function (e) {
    e.preventDefault()
    username = $("input.username").val();
    socket.emit("register_client", {username: username}, registerUsername);
});

// Register username
function registerUsername(username, roomName, msg_json){
    if (roomName) {
        $("[id^=noname]").prop("disabled", true);
    } else {
        informUser(JSON.parse(msg_json));
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
            console.log(msg);
            break;
        case "new_game":
            console.log("> Game about to start")
            runTimer(msg["timer"], function () {
                console.log(">> Start Game")
            })
            break;
        case "new_round":
            console.log("* Start round")
            runTimer(msg["timer"], function () {
                console.log("** End round")
            })
            break;
        default:
            console.error("Not expected msg type")
    }
}

function runTimer(time, callback) {
    let initialOffset = "188";
    let i = 1;

    // Initialization
    $("h2").text(time);
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