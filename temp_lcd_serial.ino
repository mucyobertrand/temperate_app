
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>

// ---- CONFIG: change these ----
LiquidCrystal_I2C lcd(0x27, 16, 2);   // I2C address, columns, rows
const String CANDIDATE_NAME = "IRASUBIZA MUCYO Bertrand"; // change to your name

#define DHT_PIN 2
#define DHT_TYPE DHT11
DHT dht(DHT_PIN, DHT_TYPE);

const float TEMP_HIGH_THRESHOLD = 30.0; // example threshold for "status"
// --------------------------------

unsigned long lastScrollTime = 0;
unsigned long lastTempReadTime = 0;
unsigned long lastSerialSendTime = 0;

int scrollIndex = 0;
const int SCROLL_DELAY = 400;          // ms between each scroll shift
const int TEMP_READ_INTERVAL = 2000;   // DHT11 needs at least ~2s between reads
const int SERIAL_SEND_INTERVAL = 2000; // send to PC every 2s

float currentTemp = 0.0;
bool lastReadValid = false;
String paddedName = "";  // name with spaces added for smooth scrolling

void setup() {
  Serial.begin(9600);
  pinMode(8, OUTPUT);
  digitalWrite(8, HIGH);

  dht.begin();

  lcd.init();
  lcd.backlight();

  // Prepare the name string for scrolling:
  if (CANDIDATE_NAME.length() > 16) {
    paddedName = CANDIDATE_NAME + "                "; // 16 trailing spaces
  } else {
    paddedName = CANDIDATE_NAME;
  }

  displayName();      // initial draw of row 1
  lcd.setCursor(0, 1);
  lcd.print("Temp: --.- C");
}

void loop() {
  unsigned long now = millis();

  // --- Scroll name on row 1 if needed ---
  if (CANDIDATE_NAME.length() > 16 && now - lastScrollTime >= SCROLL_DELAY) {
    lastScrollTime = now;
    scrollName();
  }

  // --- Read temperature periodically ---
  if (now - lastTempReadTime >= TEMP_READ_INTERVAL) {
    lastTempReadTime = now;
    currentTemp = readTemperature();
    displayTemperature(currentTemp);
  }

  // --- Send to PC over Serial periodically ---
  if (now - lastSerialSendTime >= SERIAL_SEND_INTERVAL) {
    lastSerialSendTime = now;
    sendToPC(currentTemp);
  }
}

// Reads temperature from DHT11
float readTemperature() {
  float tempC = dht.readTemperature();

  if (isnan(tempC)) {
    lastReadValid = false;
    return currentTemp; // keep last known good value instead of showing garbage
  }

  lastReadValid = true;
  return tempC;
}

// Displays the (static, short) name when no scrolling is needed
void displayName() {
  lcd.setCursor(0, 0);
  lcd.print(CANDIDATE_NAME.substring(0, 16));
}

// Shifts the visible 16-character window across paddedName, wrapping around
void scrollName() {
  int len = paddedName.length();
  String window = "";

  for (int i = 0; i < 16; i++) {
    int charIndex = (scrollIndex + i) % len;
    window += paddedName[charIndex];
  }

  lcd.setCursor(0, 0);
  lcd.print(window);

  scrollIndex = (scrollIndex + 1) % len;
}

// Updates row 2 with the current temperature
void displayTemperature(float tempC) {
  lcd.setCursor(0, 1);
  if (lastReadValid) {
    lcd.print("Temp: ");
    lcd.print(tempC, 1);
    lcd.print(" C   ");
  } else {
    lcd.print("Sensor error    ");
  }
}

// Sends "temperature,status" to PC over Serial
void sendToPC(float tempC) {
  if (!lastReadValid) {
    Serial.println("ERROR,SENSOR_FAIL");
    return;
  }
  String status = (tempC > TEMP_HIGH_THRESHOLD) ? "HIGH" : "NORMAL";
  Serial.print(tempC, 1);
  Serial.print(",");
  Serial.println(status);
}