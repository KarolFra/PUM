from flask_mqtt import Mqtt
import socket

def configure_mqtt(app):
    # Get local IP for broker selection
    local_ip = socket.gethostbyname(socket.gethostname())

    if local_ip.startswith('192.168.1.'):
        app.config['MQTT_BROKER_URL'] = '192.168.1.21'
    elif local_ip.startswith('192.168.0.'):
        app.config['MQTT_BROKER_URL'] = '192.168.0.121'
    else:
        # Default or fallback
        app.config['MQTT_BROKER_URL'] = 'localhost'

    print(f"Using MQTT Broker: {app.config['MQTT_BROKER_URL']}")

    app.config['MQTT_BROKER_PORT'] = 1883
    app.config['MQTT_USERNAME'] = ''
    app.config['MQTT_PASSWORD'] = ''
    app.config['MQTT_KEEPALIVE'] = 60
    app.config['MQTT_TLS_ENABLED'] = False
