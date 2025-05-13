let controlMode = "esp32"; // Default mode
let stopTime = 100; // Default stop time in seconds

// Fetch sensor data + distance + RPi CPU temperature
function updateSensorData() {
    // 1) Temperature & humidity
    fetch("/sensor_data")
        .then(response => response.json())
        .then(data => {
            document.getElementById("sensor-temperature-value").innerHTML =
                `<a href="/chart/temperature">${data.temperature ? data.temperature + "°C" : "No Data"}</a>`;
        })
        .catch(error => console.error("Error fetching sensor data:", error));

    // 2) Distance
    fetch('/distance')
        .then(response => response.json())
        .then(data => {
            document.getElementById('sensor-distance-value').textContent =
                data.distance !== undefined ? data.distance + " cm" : "No Data";
        });

    // 3) RPi CPU Temperature
    fetch("/rpi_temperature")
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            document.getElementById("rpi-temp-value").innerText =
                data.temperature || "No Data";
        })
        .catch(error => {
            console.error("Error fetching RPi temperature:", error);
            document.getElementById("rpi-temp-value").innerText =
                "Error, API disconnect";
        });
}

// Call updateSensorData() every 1 second
setInterval(updateSensorData, 1000);

// Initial fetch on page load
document.addEventListener("DOMContentLoaded", updateSensorData);

// Set PWM
async function setPWM(value) {
    try {
        const response = await fetch(`/set_pwm/${value}`, { method: "POST" });
        const data = await response.json();
        if (data.error) {
            alert(data.error);
        } else {
            alert(`LIGHT SET to: ${data.pwm}, (INVERSE LOGIC!!)`);
        }
    } catch (error) {
        console.error("Error setting PWM:", error);
    }
}

// Update fan speed only if in manual mode
function updateFanSpeed(value) {
    document.getElementById('fanValue').textContent = value;
    if (controlMode === "manual") {
        fetch('/set_fan_speed/' + value, { method: 'POST' })
            .then(response => response.json())
            .then(data => console.log('Fan speed:', data))
            .catch(error => console.error('Error:', error));
    }
    openModal(); //call to decouple from stop time setting
}

// Function to switch between ESP32 and Manual control
function setControlMode(mode) {
    controlMode = mode;
    fetch('/set_control_mode/' + mode, { method: 'POST' })
        .then(response => response.json())
        .then(data => console.log('Control Mode:', data))
        .catch(error => console.error('Error:', error));
}

// Modal Functions
function openModal() {
    const modal = document.getElementById('valueModal');
    const input = document.getElementById('valueInput');
    input.value = stopTime; // Set current stop time
    modal.style.display = 'block';
}

function closeModal() {
    const modal = document.getElementById('valueModal');
    modal.style.display = 'none';
}

function saveValue() {
    const input = document.getElementById('valueInput');
    const value = parseInt(input.value);
    
    if (isNaN(value) || value < 0 || value > 180) {
        alert('Please enter a value between 0 and 180');
        return;
    }

    stopTime = value; // Update the stop time
    console.log('Stop Time set to:', stopTime);
    alert(`Stop Time set to ${stopTime} seconds`);
    closeModal();
    openModal();

    // Optionally, send stop time to Flask if needed
    fetch('/set_stop_time/' + value, { method: 'POST' })
         .then(response => response.json())
         .then(data => console.log('Stop Time:', data))
         .catch(error => console.error('Error:', error));
}

// Close modal if user clicks outside it
window.onclick = function(event) {
    const modal = document.getElementById('valueModal');
    if (event.target == modal) {
        closeModal();
    }
};
