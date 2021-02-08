#define BLYNK_PRINT Serial

//<===================== VIRTUAL PINS ====================>
#define VPIN_ALARM V0
#define VPIN_BUZZER_ON_DETECT V1
#define VPIN_PUSH_NOTIFICATION V2
#define VPIN_LOG_HIST V3
#define VPIN_EMAIL_NOTIFICATION V4
#define VPIN_TABLE V5
#define VPIN_CLEAR_LOGS V6
#define VPIN_BUZZER_MANUAL V7
#define VPIN_ROW_INDEX V69

//<===================== LIBRARIES ====================>
#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
#include <TimeLib.h>
#include <WidgetRTC.h>

//<===================== OBJECTS ====================>
BlynkTimer timer;
WidgetRTC rtc;

//<===================== GLOBAL VARIABLES =====================>
char auth[] = "Qh9VT9rlG2Zlsrsy8TKS5crv01O7oaH8";
char ssid[] = "";
char pass[] = "";
int pirPin = 13;                                           // Pin D7 or GPIO13
int rowIndex = 0;

// Flags
bool isBuzzerEnabled, isSystemEnabled, isLogHistoryEnabled, isPushNotificationEnabled, isEmailNotificationEnabled;   // Flags for system features
bool activateBuzzer;
bool pirActivated;
bool isEmailSent = false;
bool isNotificationSent = false;
bool isLogSent = false;

//<===================== ESSENTIAL FUNCTIONS =====================>
String getCurrentDate() { return String(year()) + "-" + month() + "-" + day(); }
String getCurrentTime() { return String(hour()) + ":" + minute(); }
String getCurrentTime12() { return String(hourFormat12()) + ":" + minute() + (isPM() ? "PM" : "AM"); }

void send_log()
{
  if(isLogHistoryEnabled && isSystemEnabled && pirActivated)
  {
    if(!isLogSent)
    {
      String logMsg = "Motion Detected.";
      Blynk.virtualWrite(VPIN_TABLE, "add", rowIndex, getCurrentTime12() + " - " + logMsg, getCurrentDate());
      Blynk.virtualWrite(VPIN_TABLE, "pick", rowIndex);

      // Log successfully sent. Raise the flag to prevent flooding
      // the server with logs
      isLogSent = true;

      // Update row index. Both global variable and virtual pin.
      rowIndex++;
      Blynk.virtualWrite(VPIN_ROW_INDEX, rowIndex);
    }
  }
}

// Sends both email and push notification
void send_notification()
{
  if(isSystemEnabled && pirActivated)
  {
    if(!isNotificationSent)
    {
      if(isEmailNotificationEnabled)  Blynk.email("Blynk: {DEVICE_NAME} Motion Sensor", "Motion Detected.");
      if(isPushNotificationEnabled)   Blynk.notify("{DEVICE_NAME} Motion Detected.");

      isNotificationSent = true;
    }
  }
}
//<===================== SENSOR FUNCTIONS =====================>
void sensor()
{
  //Check if the Pin is HIGH
  //Check if the Buzzer is enabled and system enabled
  //Send notification and logs
  Blynk.syncVirtual(VPIN_ALARM);
  bool isMotionDetected = bool(digitalRead(pirPin));

  if(isMotionDetected && !pirActivated)
  {
    // Serial.println("Door Opened");
    pirActivated = true;
    if(isBuzzerEnabled)
    {
      Blynk.virtualWrite(VPIN_BUZZER_MANUAL, HIGH);
      Blynk.syncVirtual(VPIN_BUZZER_MANUAL);
    }
  }
  else if (!isMotionDetected && pirActivated)
  {
    // Serial.println("Door Closed");
    pirActivated = false;
    isLogSent = false;
    isNotificationSent = false;
  }
}
//<===================== BUILTIN BLYNK FUNCTIONS =====================>
BLYNK_WRITE(VPIN_ALARM)               { isSystemEnabled = bool(param.asInt()); }
BLYNK_WRITE(VPIN_PUSH_NOTIFICATION)   { isPushNotificationEnabled = bool(param.asInt()); }
BLYNK_WRITE(VPIN_EMAIL_NOTIFICATION)  { isEmailNotificationEnabled = bool(param.asInt()); }
BLYNK_WRITE(VPIN_BUZZER_ON_DETECT)    { isBuzzerEnabled = bool(param.asInt()); }
BLYNK_WRITE(VPIN_BUZZER_MANUAL)       { activateBuzzer = bool(param.asInt()); }
BLYNK_WRITE(VPIN_LOG_HIST)            { isLogHistoryEnabled = bool(param.asInt()); }
BLYNK_WRITE(VPIN_ROW_INDEX)           { rowIndex = param.asInt(); }

/*
  BLYNK_CONNECTED runs everytime the device establishes a
  connection to the Blynk server.
*/
BLYNK_CONNECTED() {
  // Synchronize ALL virtual pins
  Blynk.syncVirtual(VPIN_ALARM,
                    VPIN_BUZZER_ON_DETECT,
                    VPIN_PUSH_NOTIFICATION,
                    VPIN_LOG_HIST,
                    VPIN_EMAIL_NOTIFICATION,
                    VPIN_TABLE,
                    VPIN_CLEAR_LOGS,
                    VPIN_BUZZER_MANUAL,
                    VPIN_ROW_INDEX);

  // Synchronize device clock with the Blynk server's clock
  rtc.begin();
}

//<===================== PROGRAM START =====================>
void setup()
{
  Serial.begin(9600);

  Serial.println("Waiting 30 seconds for pir sensor to setup...");
  delay(30000); //Wait 30 seconds for the PIR sensor to setup

  //Please enter your Server IP address
  Blynk.begin(auth, ssid, pass, IPAddress(192,168,0,0), 8080);
  // Clock sync interval in seconds (10 minutes)
  setSyncInterval(10 * 60);

  // Set buzzer pin as OUTPUT and start in OFF state
  pinMode(pirPin, INPUT);

  timer.setInterval(1000L, send_log);
  timer.setInterval(5000L, send_notification);
  timer.setInterval(100L, sensor);
}

void loop()
{
  Blynk.run();
  timer.run();
}
