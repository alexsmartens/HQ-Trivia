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
            console.log(msg["msg"]);
            break;
        default:
            console.error("Not expected msg type")
    }
}