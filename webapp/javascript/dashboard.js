const websocket = new OBSWebSocket();

let connected = false;
let obs_finished = false;
let streamheart_finished = false;
let activeScene;

websocket.connect({
    address: '192.168.178.24:4445'
    })
    .then(() => {
        connected = true;

        return websocket.send('OBS Studio', 'GetSceneList');
    })
    .then(data => {
        const containerFirst = document.getElementById('containerFirst');

        data.scenes.forEach(scene => {
            let sceneButton = document.createElement('button');
            sceneButton.setAttribute('class', 'grid-item control_button');
            sceneButton.setAttribute('id', `${scene.name}`);
            sceneButton.textContent = scene.name;

            sceneButton.onclick = function () {
                websocket.send('OBS Studio', 'SetCurrentScene', {
                    'scene-name': scene.name
                });
            };

            containerFirst.appendChild(sceneButton);
        });

        activeScene = document.getElementById(`${data.currentScene}`);
        activeScene.disabled = true;

        return websocket.send('OBS Studio', 'GetStreamingStatus');
    })
    .then(data => {
        let streamButton = document.getElementById('start_stream');
        streamButton.onclick = function () {
            if (!streamButton.classList.contains('streaming')) {
                websocket.send('OBS Studio', 'SetCurrentScene', {'scene-name': 'Start'});
            }

            websocket.send('OBS Studio', 'StartStopStreaming');
        };
        if (data.streaming === true) {
            streamButton.classList.toggle('streaming');
            streamButton.textContent = "Stream beenden";
        }

        return websocket.send('OBS Studio', 'GetSceneItemProperties', {'item': 'Overlay', 'scene-name': 'Live'});
    })
    .then(data => {
        if (!data.visible) {
            let overlay = document.getElementById('overlay_hide');

            if (overlay) {
                overlay.id = 'overlay_hide_pressed';
                overlay.classList.toggle('button_pressed');
            }
        }

        obs_finished = true;

        return websocket.send('Heartrate', 'GetBrbStatus');
    })
    .then(data => {
        if (!data.enabled) {
            let brb_button = document.getElementById('auto_brb');
            brb_button.classList.add('button_pressed');
            brb_button.textContent = 'Auto BRB OFF';
        }

        streamheart_finished = true;
        show();
    })
    .catch(err => { // Promise convention dicates you have a catch on every chain.
        if (!connected) {
            console.log("Error to connect to server: ", err);
        } else if (!obs_finished) {
            console.log("OBS closed", err);
        } else if (!streamheart_finished) {
            console.log("Streamheart closed", err);
        }
    });


function showPosition(position) {
    console.log("Latitude: " + position.coords.latitude + "Longitude: " + position.coords.longitude);
    websocket.send_update('CurrentPosition', {
        'latitude': position.coords.latitude,
        'longitude': position.coords.longitude
    });
}

function showError(error) {
    let errorMsg = "";

    switch (error.code) {
        case error.PERMISSION_DENIED:
            errorMsg = "User denied the request for Geolocation";
            console.log("User denied the request for Geolocation.");
            break;
        case error.POSITION_UNAVAILABLE:
            errorMsg = "Location information is unavailable";
            console.log("Location information is unavailable.");
            break;
        case error.TIMEOUT:
            errorMsg = "The request to get user location timed out";
            console.log("The request to get user location timed out.");
            break;
        case error.UNKNOWN_ERROR:
            errorMsg = "An unknown error occurred";
            console.log("An unknown error occurred.");
            break;
    }

    websocket.send_update('CurrentPosition', {'error': errorMsg});
}

function position() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(showPosition, showError);
    } else {
        console.log("Geolocation is not supported by this browser.");
    }
}

websocket.on('GetPosition', () => {
    position()
})

websocket.on('UnsubscribedFrom', () => {
    document.getElementById('main').classList.toggle('show');
    document.getElementById('error').classList.toggle('show');
})

websocket.on('SwitchScenes', data => {
    activeScene.disabled = false;
    let doc = document.getElementById(`${data.sceneName}`);

    if (doc) {
        activeScene = doc;
    }

    activeScene.disabled = true;
})

websocket.on('StreamStarted', () => {
    let streamButton = document.getElementById('start_stream');
    streamButton.classList.toggle('streaming');
    streamButton.textContent = "Stream beenden";
})

websocket.on('StreamStopped', () => {
    let streamButton = document.getElementById('start_stream');
    streamButton.classList.toggle('streaming');
    streamButton.textContent = "Go live";
})

websocket.on('SceneItemVisibilityChanged', data => {
    if (data.itemName === 'Overlay') {
        if (data.itemVisible) {
            let overlayButton = document.getElementById('overlay_hide_pressed');
            overlayButton.id = 'overlay_hide';
            overlayButton.classList.toggle('button_pressed');
        } else {
            let overlayButton = document.getElementById('overlay_hide');
            overlayButton.id = 'overlay_hide_pressed';
            overlayButton.classList.toggle('button_pressed');
        }
    }
})

websocket.on('BrbDisabled', () => {
    let brb_button = document.getElementById('auto_brb');
    brb_button.classList.add('button_pressed');
    brb_button.textContent = 'Auto BRB OFF';
})

websocket.on('BrbEnabled', () => {
    let brb_button = document.getElementById('auto_brb');
    brb_button.classList.remove('button_pressed');
    brb_button.textContent = 'Auto BRB ON';
})

websocket.on('Exiting', () => {
    document.getElementById('main').classList.toggle('show');
    document.getElementById('error').classList.toggle('show');
})

websocket.on('error', err => {
    console.error('Fehler:', err);
});

async function show() {
    await sleep(600);
    document.getElementById('main').classList.toggle('show');
    document.getElementById('error').classList.toggle('show');
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function openPage(pageName, elmnt, color) {
    let i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName('tabcontent');
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = 'none';
    }
    tablinks = document.getElementsByClassName('tablink');
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].style.backgroundColor = "";
    }
    document.getElementById(pageName).style.display = 'block';
    elmnt.style.backgroundColor = color;
}

// Get the element with id="defaultOpen" and click on it
document.getElementById('defaultOpen').click();

async function refresh() {
    websocket.send('OBS Studio', 'SetCurrentSceneCollection', {'sc-name': 'Refresh'});
    await sleep(1000);
    websocket.send('OBS Studio', 'SetCurrentSceneCollection', {'sc-name': 'Main'});
}

async function refresh_overlay() {
    websocket.send('OBS Studio', 'SetSceneItemProperties', {'item': 'Overlay', 'visible': false});
    await sleep(1000);
    websocket.send('OBS Studio', 'SetSceneItemProperties', {'item': 'Overlay', 'visible': true});
}

async function hide_overlay() {
    let overlay = document.getElementById('overlay_hide');

    if (overlay) {
        websocket.send('OBS Studio', 'SetSceneItemProperties', {'item': 'Overlay', 'visible': false});
    } else {
        websocket.send('OBS Studio', 'SetSceneItemProperties', {'item': 'Overlay', 'visible': true});
    }
}

async function toggle_auto_brb() {
    let brb_button = document.getElementById('auto_brb');

    if (brb_button.classList.contains('button_pressed')) {
        websocket.send('Heartrate', 'EnableBrb');
    } else {
        websocket.send('Heartrate', 'DisableBrb');
    }
}

async function screenshot() {
}
