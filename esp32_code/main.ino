#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>
#include <Adafruit_Fingerprint.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>
#include <HardwareSerial.h>
#include <Keypad.h> // Keypad
#include <ArduinoJson.h>

// === CONFIGURATION ===
const char* WIFI_SSID = "YourWifiName";
const char* WIFI_PASS = "YourWifiPassword";
// Use your computer's IP address where Django is running not localhost or 127.0.0.1.
const char* DJANGO_SERVER_IP = "192.168.43.52";
const int DJANGO_SERVER_PORT = 8080;

// OLED Setup
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1 // No reset pin on most OLED modules
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

#define LED_PIN 2  // Onboard LED pin (Blue on ESP32)

HardwareSerial mySerial(2); // Using UART2 for fingerprint sensor (GPIO16/RX, GPIO17/TX)
Adafruit_Fingerprint finger(&mySerial);

// Server
WebServer server(80);

// Keypad Setup
const byte ROWS = 4;
const byte COLS = 4;
char keys[ROWS][COLS] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'},
};
byte rowPins[ROWS] = {5, 18, 19, 23};
byte colPins[COLS] = {13, 14, 27, 26};

// Create the Keypad
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);
String inputBuffer = ""; // To store multi-digit input

// === STATE MANAGEMENT & POLLING TIMER ===
bool sessionActive = false;
String activeCourseCode = "";
int lecturerFingerprintId = 0;

unsigned long lastPollTime = 0;
const long pollInterval = 5000; // Poll for new commands every 5 seconds

// === Function to print to Serial and OLED ===
void showMessage(String msg, bool clear = true, int delay_ms = 0) {
  if (clear) display.clearDisplay();
  display.display();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0, 0);
  display.println(msg);
  display.display();
  Serial.println(msg);

  if (delay_ms > 0) {

    delay(delay_ms);

  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // Setup onboard LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Setup fingerprint sensor
  mySerial.begin(57600, SERIAL_8N1, 16, 17);
  finger.begin(57600);
  delay(100);

  // Setup OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED not found");
    while (1);
  }
  display.clearDisplay();
  display.display();

  // Fingerprint sensor check
  if (finger.verifyPassword()) {
    showMessage("Sensor OK", true, 500);
  } else {
    showMessage("Sensor not found!");
    blinkLED(5, 100);
    while (1);
  }

  // Setup WIFI
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());

  // Enable http://esp32.local/
  if (MDNS.begin("esp32")) {
    Serial.println("mDNS responder started at esp32.local");
  } else {
    Serial.println("Error setting up mDNS responder!");
  }

  showMessage("Syncing state...", true, 1000);
  syncSessionState();

  // If no session was resumed, show the main menu
  if (!sessionActive) {
    showMenu();
  }
}

void loop() {

  ensureWiFiConnected();

  if (sessionActive) {
    // If a session is active, the device's only job is to wait for fingerprints
    handleActiveSession();
  } else {
    // If no session is active, listen for keypad input to show the menu
    handleMainMenu();

    if (millis() - lastPollTime >= pollInterval) {
      lastPollTime = millis();
      pollForCommands();
    }
  }
  delay(50); // Small delay to prevent busy-waiting
}

// --- Handles menu navigation when no class session is active ---
void handleMainMenu() {
  char key = keypad.getKey();
  if (key != NO_KEY) {
    if (isDigit(key)) {
      inputBuffer += key;
      Serial.print(key);
      // Also update OLED to show current buffer
      clearOLEDPortion(0, 35, 128, 30);
      display.setCursor(0, 35);
      display.print(inputBuffer);
      display.display();
    }
    else if (key == '*') {
      // Backspace: remove last character (if any)
      if (inputBuffer.length() > 0) {
        inputBuffer.remove(inputBuffer.length() - 1);
        Serial.println();
        Serial.print("Enter choice: ");
        Serial.print(inputBuffer);
        // Also update OLED to show current buffer
        clearOLEDPortion(0, 35, 128, 30);
        display.setCursor(0, 35);
        display.print(inputBuffer);
        display.display();
      }
    }
    else if (key == 'D') {
      // Cancel current entry and go back to the menu
      inputBuffer = "";
      Serial.println();            // move to a new line on Serial
      showMenu();                  // return to menu on Serial + OLED
    }

    else if (key == '#') {
      Serial.println();
      int choice = inputBuffer.toInt();
      inputBuffer = "";
      if (choice == 1) {
        startAttendanceSession();
      } else {
        showMessage("Invalid option.", true, 1000);
      }
      // Wait until key is released
      char dummyKey;
      do {
        dummyKey = keypad.getKey();
        delay(5);
      } while (dummyKey != NO_KEY);

      inputBuffer = "";
      showMenu();
    }
  }
  delay(50);
}

// === Handles logic when a class session is active ===
void handleActiveSession() {
  showMessage("Session Active: " + activeCourseCode + "\nScan finger...", false);

  int fingerId = getVerifiedFingerprintID(500); // Check for a finger briefly

  if (fingerId > 0) { // A valid finger was found
    if (fingerId == lecturerFingerprintId) {
      // The lecturer scanned again, so end the session
      endAttendanceSession(fingerId);
    } else {
      // It's a student, so mark their attendance
      markStudentAttendance(fingerId, activeCourseCode);
    }
    // After an action, pause and refresh the screen
    delay(2000);
    showMessage("Session Active: " + activeCourseCode + "\nScan finger...");
  }
}

// === API-DRIVEN FUNCTIONS ===

void startAttendanceSession() {
  ensureWiFiConnected();

  if(WiFi.status() != WL_CONNECTED) {
      showMessage("No WiFi!", true, 2000);
      return;
  }
  
  showMessage("Lecturer Scan Finger");
  int fingerId = getVerifiedFingerprintID(10000); // 10-second timeout for lecturer
  if (fingerId <= 0) {
    showMessage("Start failed: No finger", true, 1500);
    return;
  }

  String courseCode = readKeypadInput("Enter Course Code:");
  if (courseCode == "") {
    showMessage("Start failed: No code", true, 1500);
    return;
  }
  courseCode.toUpperCase();
  HTTPClient http;
  String apiUrl = "http://" + String(DJANGO_SERVER_IP) + ":" + String(DJANGO_SERVER_PORT) + "/session/start/";
  http.begin(apiUrl);
  http.addHeader("Content-Type", "application/json");

  // Create JSON payload using ArduinoJson
  StaticJsonDocument<200> doc;
  doc["fingerprint_id"] = fingerId;
  doc["course_code"] = courseCode;
  String payload;
  serializeJson(doc, payload);


  // For debugging, print the payload you are about to send
  Serial.print("Sending payload: ");
  Serial.println(payload);

  int httpResponseCode = http.POST(payload);

  if (httpResponseCode > 0) { // Check for a positive HTTP status code
    String responseBody = http.getString();
    if (httpResponseCode == 201) { // 201 Created
      // Set the state to active
      sessionActive = true;
      activeCourseCode = courseCode;
      lecturerFingerprintId = fingerId;
      showMessage("Session Started!", true, 2000);
    } else {
      // Received an error response from the server (e.g., 400, 404, 500)
      Serial.print("HTTP POST failed, error code: ");
      Serial.println(httpResponseCode);
      Serial.println("Response: " + responseBody);
      showMessage("Start Failed!\n" + responseBody, true, 3000);
    }
  } else {
    // This is a client-side connection error
    Serial.printf("[HTTP] POST... failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
    showMessage("Conn. Failed!\n" + http.errorToString(httpResponseCode), true, 3000);
  }
  http.end();
}

void markStudentAttendance(int studentId, String courseCode) {
  ensureWiFiConnected();

  if(WiFi.status() != WL_CONNECTED) {
    showMessage("No WiFi!\nTry again.", true, 2000);
    return; // Stop if we couldn't reconnect
  }

  HTTPClient http;
  String apiUrl = "http://" + String(DJANGO_SERVER_IP) + ":" + String(DJANGO_SERVER_PORT) + "/attendance/mark/";
  http.begin(apiUrl);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<200> doc;
  doc["fingerprint_id"] = studentId;
  doc["course_code"] = courseCode;
  String payload;
  serializeJson(doc, payload);

  int httpResponseCode = http.POST(payload);
  String responseBody = http.getString();

  StaticJsonDocument<200> responseDoc;
  deserializeJson(responseDoc, responseBody);
  String message = responseDoc["message"];

  if (httpResponseCode == 201 || httpResponseCode == 200) {
    showMessage("OK: " + message, true, 2000);
  } else {
    showMessage("FAIL: " + message, true, 2000);
  }
  http.end();
}

void endAttendanceSession(int fingerId) {
  ensureWiFiConnected();

  if(WiFi.status() != WL_CONNECTED) {
      showMessage("No WiFi!", true, 2000);
      return;
  }

  showMessage("Ending session...");
  HTTPClient http;
  String apiUrl = "http://" + String(DJANGO_SERVER_IP) + ":" + String(DJANGO_SERVER_PORT) + "/session/end/";
  http.begin(apiUrl);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<100> doc;
  doc["fingerprint_id"] = fingerId;
  String payload;
  serializeJson(doc, payload);

  int httpResponseCode = http.POST(payload);

  if (httpResponseCode == 200) {
    showMessage("Session Ended!", true, 2000);
    // Reset state back to idle
    sessionActive = false;
    activeCourseCode = "";
    lecturerFingerprintId = 0;
  } else {
    String responseBody = http.getString();
    showMessage("End Failed!\n" + responseBody, true, 3000);
  }
  http.end();
}


// === READ INPUT FROM KEYPAD (with backspace) ===
String readKeypadInput(String prompt) {
  inputBuffer = "";
  showMessage(prompt, true);
  display.setCursor(0, 20);
  display.print("Input: ");
  display.display();
  
  unsigned long startTime = millis();
  while(millis() - startTime < 15000) { // 15 second timeout
    char key = keypad.getKey();
    if (key != NO_KEY) {
      // Reset the timeout timer on any keypress
      startTime = millis(); 
      
      if (key == '#') {
        Serial.println();
        return inputBuffer; // Return the completed input
      }
      // Allow alphanumeric characters (useful for course codes like 'A' or 'B')
      if (isalnum(key)) {
        inputBuffer += key;
      }
      if (key == '*') { // Backspace
        if (inputBuffer.length() > 0) {
            inputBuffer.remove(inputBuffer.length() - 1);
        }
      }
      
      // Update the display with the current input
      Serial.println("Input: " + inputBuffer);
      display.fillRect(0, 20, 128, 10, BLACK); // Clear previous input
      display.setCursor(0, 20);
      display.print("Input: " + inputBuffer);
      display.display();
    }
  }
  showMessage("Input timed out!", true, 1500);
  return ""; // Return empty string on timeout
}

// DISPLAY MENU
void showMenu() {
  // Serial monitor
  Serial.println("\n=== Main Menu ===");
  Serial.print("Enter 1 to start: ");

  // OLED
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("=== Main Menu ===");
  display.println("Enter 1 to start: ");
  display.display();
}

// === Blink LED for errors or alerts ===
void blinkLED(int times, int delayTime) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(delayTime);
    digitalWrite(LED_PIN, LOW);
    delay(delayTime);
  }
}

// === ENROLLMENT LOGIC ===
void enrollFingerprint() {
  String idStr = readKeypadInput("Enter ID (1-1000):"); 
  
  // If the user cancelled or it timed out, stop.
  if (idStr == "") return; 

  int id = idStr.toInt(); // Convert the returned string to an integer

  if (id < 1 || id > 1000) {
    showMessage("Invalid ID!");
    blinkLED(3, 150);
    return;
  }

  showMessage("Enrolling ID #" + String(id));
  if (getFingerprintEnroll(id)) {
    showMessage("Enrollment OK");
    digitalWrite(LED_PIN, HIGH); delay(1000); digitalWrite(LED_PIN, LOW);
  } else {
    showMessage("Enrollment Failed");
    blinkLED(3, 150);
  }
}

// --- A function that waits for a finger and returns its ID ---
int getVerifiedFingerprintID(int timeout) {
  uint8_t p = FINGERPRINT_NOFINGER;
  unsigned long startTime = millis();

  while (p != FINGERPRINT_OK) {
    if (millis() - startTime > timeout) {
      return -1; // Timeout
    }
    p = finger.getImage();
  }

  // Found a finger
  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) return -2; // Error

  p = finger.fingerSearch();
  if (p != FINGERPRINT_OK) return -3; // Not found

  // Found a match
  digitalWrite(LED_PIN, HIGH); delay(200); digitalWrite(LED_PIN, LOW);
  return finger.fingerID;
}

String getFingerprintEnroll(uint8_t id) {
    int p = -1;
    showMessage("Place finger...");
    delay(500);

    // First fingerprint image
    unsigned long startTime = millis();
    while (p != FINGERPRINT_OK) {
        if (millis() - startTime > 10000) return "Enrollment Timeout!";
        p = finger.getImage();
    }
    showMessage("Image 1 OK");
    if (finger.image2Tz(1) != FINGERPRINT_OK) return "Image 1 conversion failed.";

    showMessage("Remove finger");
    delay(2000);
    while (finger.getImage() != FINGERPRINT_NOFINGER);

    // Second fingerprint image
    showMessage("Place again...");
    p = -1;
    startTime = millis();
    while (p != FINGERPRINT_OK) {
        if (millis() - startTime > 10000) return "Enrollment Timeout!";
        p = finger.getImage();
    }
    showMessage("Image 2 OK");
    if (finger.image2Tz(2) != FINGERPRINT_OK) return "Image 2 conversion failed.";
    
    showMessage("Creating model...");
    if (finger.createModel() != FINGERPRINT_OK) return "Model creation failed.";
    
    showMessage("Storing ID #" + String(id));
    if (finger.storeModel(id) != FINGERPRINT_OK) return "Storing model failed.";

    return "Enrollment successful."; // Success message
}

// === VERIFICATION LOGIC ===
void verifyFingerprint() {
  showMessage("Place finger to verify");

  unsigned long startTime = millis();
  uint8_t p = FINGERPRINT_NOFINGER;

  while (millis() - startTime < 5000) {
    p = finger.getImage();
    if (p == FINGERPRINT_OK) break;
    delay(100);
  }

  if (p != FINGERPRINT_OK) {
    showMessage("No finger or error");
    blinkLED(3, 150);
    return;
  }

  if (finger.image2Tz() != FINGERPRINT_OK) {
    showMessage("Template error");
    return;
  }

  p = finger.fingerSearch();
  if (p == FINGERPRINT_OK) {
    showMessage("Verified ID: " + String(finger.fingerID));
    digitalWrite(LED_PIN, HIGH); delay(1000); digitalWrite(LED_PIN, LOW);
  } else {
    showMessage("Not Found");
    blinkLED(2, 100);
  }
}

// === LIST ALL TEMPLATES ===
void listFingerprints() {
  finger.getTemplateCount();
  if (finger.templateCount == 0) {
    showMessage("No templates stored");
    return;
  }

  Serial.print("Sensor reports "); Serial.print(finger.templateCount); Serial.println(" templates.");
  for (int i = 1; i <= 127; i++) {
    if (finger.loadModel(i) == FINGERPRINT_OK) {
      Serial.print("Template found at ID #"); Serial.println(i);
    }
  }
  showMessage("Done listing");
}

// === DELETE SPECIFIC TEMPLATE ===
void deleteFingerprint() {
  String idStr = readKeypadInput("Enter ID to delete:");

  // If the user cancelled or it timed out, stop.
  if (idStr == "") return;

  int id = idStr.toInt(); // Convert the returned string to an integer

  if (id < 1 || id > 1000) {
    showMessage("Invalid ID");
    blinkLED(3, 150);
    return;
  }

  uint8_t p = finger.deleteModel(id);
  if (p == FINGERPRINT_OK) {
    showMessage("ID " + String(id) + " deleted");
    digitalWrite(LED_PIN, HIGH); delay(500); digitalWrite(LED_PIN, LOW);
  } else {
    showMessage("Delete Failed");
    blinkLED(3, 150);
  }
}

void syncSessionState() {
  ensureWiFiConnected(); // Make sure we're online before trying to sync
  
  HTTPClient http;
  String apiUrl = "http://" + String(DJANGO_SERVER_IP) + ":" + String(DJANGO_SERVER_PORT) + "/session/status/";
  http.begin(apiUrl);

  int httpResponseCode = http.GET();

  if (httpResponseCode == 200) {
    String responseBody = http.getString();
    StaticJsonDocument<200> doc;
    deserializeJson(doc, responseBody);

    String status = doc["status"];
    if (status == "active") {
      // An active session was found on the server, resume it
      activeCourseCode = doc["course_code"].as<String>();
      lecturerFingerprintId = doc["lecturer_fingerprint_id"].as<int>();
      sessionActive = true;
      Serial.println("Resumed active session for course: " + activeCourseCode);
      showMessage("Resumed Session:\n" + activeCourseCode, true, 2000);
    } else {
      // No active session on the server
      sessionActive = false;
      activeCourseCode = "";
      lecturerFingerprintId = 0;
      Serial.println("No active session found on server. Starting fresh.");
    }
  } else {
    Serial.printf("[HTTP] GET... failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
    showMessage("Sync Failed!", true, 2000);
  }
  http.end();
}

// CHECK WIFI CONNECTION
void ensureWiFiConnected() {
  if (WiFi.status() != WL_CONNECTED) {
    showMessage("Reconnecting WiFi...", true);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED && retries < 20) { // Try for 10 seconds
      delay(500);
      Serial.print(".");
      retries++;
    }
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWiFi reconnected.");
      Serial.print("ESP32 IP Address: ");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("\nFailed to reconnect WiFi.");
      showMessage("WiFi Failed!", true, 2000);
    }
  }
}

// === REPORT ENROLLMENT RESULT TO SERVER ===
void reportEnrollmentResult(int taskId, bool success, String message) {
    ensureWiFiConnected();
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Failed to report result: No WiFi.");
        return;
    }

    HTTPClient http;
    String apiUrl = "http://" + String(DJANGO_SERVER_IP) + ":" + String(DJANGO_SERVER_PORT) + "/api/report-enrollment-result/";
    http.begin(apiUrl);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<200> doc;
    doc["task_id"] = taskId;
    doc["status"] = success ? "success" : "error";
    doc["message"] = message;

    String payload;
    serializeJson(doc, payload);

    Serial.println("Reporting result: " + payload);
    http.POST(payload); // We send the result but don't need to check the response
    http.end();
}

// === POLL SERVER FOR PENDING COMMANDS ===
void pollForCommands() {
    Serial.println("Polling for commands...");
    ensureWiFiConnected();
    if (WiFi.status() != WL_CONNECTED) return;

    HTTPClient http;
    String apiUrl = "http://" + String(DJANGO_SERVER_IP) + ":" + String(DJANGO_SERVER_PORT) + "/api/get-device-command/";
    http.begin(apiUrl);

    int httpResponseCode = http.GET();

    if (httpResponseCode == 200) {
        String responseBody = http.getString();
        StaticJsonDocument<200> doc;
        deserializeJson(doc, responseBody);

        String command = doc["command"];

        if (command == "enroll") {
            int slot = doc["slot"];
            int taskId = doc["task_id"];
            
            showMessage("Enroll request for\nslot #" + String(slot), true, 2000);

            // Execute the enrollment process
            String resultMessage = getFingerprintEnroll(slot);
            bool success = (resultMessage == "Enrollment successful.");

            if (success) {
                showMessage("Enrollment OK!", true, 1500);
            } else {
                showMessage("Enroll Failed:\n" + resultMessage, true, 3000);
            }
            
            // Report the result back to the server
            reportEnrollmentResult(taskId, success, resultMessage);

            // Return to the main menu
            showMenu();
        } else {
            Serial.println("No commands pending.");
        }
    } else {
        Serial.printf("[HTTP] Poll failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
}


// === CLEAR A PORTION OF THE SCREEN ===
void clearOLEDPortion(int x, int y, int width, int height) {
  display.fillRect(x, y, width, height, SSD1306_BLACK); // Black is the default background color
  display.display();  // Push changes to display
}