# Loxone-MQTT Bridge

## 🚀 Introduction

The **Loxone-MQTT Bridge** is a backend service working as a bridge between **Loxone UDP messages** and **MQTT** communication. It enables Loxone devices to connect to an MQTT broker, allowing seamless integration into Smart Home solutions like Zigbee, Philips Hue, and more.

---

## 📋 Features

- Receives and processes **UDP messages** from Loxone devices.
- Forwards these messages as MQTT messages to an MQTT broker.
- Accepts incoming MQTT messages and optionally translates them back into UDP for Loxone.
- Configuration files for devices and MQTT broker setup.
- RESTful API using **FastAPI** for controlled management.
- Supports Docker container deployment.

---

## 🧰 Dependencies

### Installed Modules
The service is built on the following Python libraries:
- **FastAPI** - REST API Framework
- **MQTT** - **fastapi-mqtt** and **gmqtt** for MQTT communication
- **asyncio** - Asynchronous event handling
- **aiodns** - Asynchronous DNS resolution
- **colorlog** - Colored log output for debugging

Check the `requirements.txt` file for the full list of dependencies.

---

## 📂 Project Structure

```plaintext
├── main.py                  # Entry point of the application
├── udp.py                   # UDP handling protocol
├── logger.py                # Logging configuration
├── constants.py             # Constants for UDP/MQTT ports, etc.
├── init_config.py           # Initial configuration generators
├── config/
│   ├── mqtt.json            # Configuration file for the MQTT broker
│   ├── devices.json         # Device information and models
│   ├── loxone.json          # Loxone device settings
│   └── models.json          # Device functionalities and mappings
├── frontend-html/           # Frontend for visualization
├── Dockerfile               # Docker configuration file
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (Development)
└── .env.prod                # Environment variables (Production)
```

---

## ⚙️ Configuration

### 1. Environment Variables

Environment variables are controlled using `.env` files:

- **API_PORT**: Port for the REST API (default: `5600`)
- **UDP_PORT**: Port for UDP communication (default: `4444`)
- **TZ**: Timezone of the container (e.g., `Europe/Berlin`)

#### Example `.env` (Development):
```dotenv
PRODUCTION=False
DOCKERFILE=Dockerfile.dev
RELOAD=--reload
API_PORT=5600
UDP_PORT=4444
TZ="Europe/Berlin"
```

---

### 2. JSON Configuration Files

#### MQTT Broker (`mqtt.json`)
Defines the connection settings for the MQTT broker:
```json
{
    "HOST": "mosquitto",
    "PORT": 1883,
    "USERNAME": "",
    "PASSWORD": "",
    "SSL": "0",
    "LAST_CONNECTION_TIME": ""
}
```

#### Devices (`devices.json`)
Defines the devices handled by the bridge:
```json
{
    "kitchen_switch": "TS0044_2",
    "kitchen_window": "ZG-102ZA",
    "bath_window": "ZG-102ZA",
    "kitchen_plug": "A7Z",
    "lovely_flower_": "TS0601_soil_3",
    "bath_presence": "ZG-204ZH",
    "living_plug": "E22x4",
    "living_lamp": "HueWhite1600"
}
```

#### Loxone Settings (`loxone.json`)
Defines the IP address and UDP port for Loxone:
```json
{
    "ip-address": "192.168.0.5",
    "udp-port": 4444
}
```

#### Models (`models.json`)
Defines the functionality of the devices:
```json
{
  "models": [
    {
      "name": "TS0044_2",
      "mqtt_topic": "zigbee2mqtt",
      "description": "Wireless switch with 4 buttons",
      ...
    }
  ]
}
```

---

## ▶️ Running the Project

### 1. Local Environment

#### Prerequisite: Python
1. **Python Version**: 3.13 (or higher).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the application:
   ```bash
   python main.py
   ```

### 2. Using Docker

#### Development:
1. Build the Docker image:
   ```bash
   docker build -t loxone-mqtt-bridge .
   ```
2. Start the container:
   ```bash
   docker run --env-file .env -p 5600:5600 loxone-mqtt-bridge
   ```

---

## 📡 Available APIs

1. **Base API URL**: `http://localhost:5600`
2. Key Endpoints:
   - **`GET /mqtt-broker-information`** – Retrieve MQTT broker connection information.
   - **`POST /mqtt-broker-connect`** – Connect using new MQTT broker credentials.
   - **`GET /api/models`** – Retrieve supported device model configurations.
   - **`POST /api/models`** – Update device model configurations.
   - **`GET /api/restart`** – Restart the server.

---

## 🌟 Features Explained

1. **UDP Processing**:
   - Receives Loxone UDP messages and forwards them as MQTT messages to the configured topic.
   - Example: UDP data `kitchen_switch/1_single` → MQTT topic `zigbee2mqtt/kitchen_switch/set`.

2. **MQTT Processing**:
   - Receives MQTT messages and translates them into UDP packets for Loxone devices.

3. **Centralized Configuration**:
   - Device and MQTT broker configurations are stored in JSON files and dynamically loaded.

---

## 🛠 Troubleshooting

1. **Issue**: MQTT is not working.
   - **Solution**: Verify the `mqtt.json` file for correct MQTT broker connection details.

2. **Issue**: Loxone UDP data is not being received.
   - **Solution**: Make sure the UDP port settings in the `loxone.json` file are correct.

3. **Logs**: Errors are displayed in color for enhanced debugging.

---

## 🖋 Authors

- **Franz Krenn** – Developer and Maintainer (Email: [office@fkrenn.at](mailto:office@fkrenn.at))

---

## ⚖️ License

This project is licensed under the **MIT License**.

---

### Enjoy working with the Loxone-MQTT Bridge! 😊