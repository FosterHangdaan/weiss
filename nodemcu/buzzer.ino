// Comment this out to disable prints and save space
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
int buzzerPin = 14;                                           // Pin D5 or GPIO14
int rowIndex = 0;

// Flags
bool isBuzzerEnabled, isSystemEnabled, isLogHistoryEnabled, isPushNotificationEnabled, isEmailNotificationEnabled;   // Flags for system features
bool activateBuzzer;
bool isEmailSent = false;
bool isNotificationSent = false;
bool isLogSent = false;

//<===================== ESSENTIAL FUNCTIONS =====================>
String getCurrentDate() { return String(year()) + "-" + month() + "-" + day(); }
String getCurrentTime() { return String(hour()) + ":" + minute(); }
String getCurrentTime12() { return String(hourFormat12()) + ":" + minute() + (isPM() ? "PM" : "AM"); }

void send_log()
{
  if(isLogHistoryEnabled && isSystemEnabled && activateBuzzer)
  {
    if(!isLogSent)
    {
      Blynk.syncVirtual(VPIN_ROW_INDEX);
      String logMsg = "Buzzer activated.";
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
  if(isSystemEnabled && activateBuzzer)
  {
    if(!isNotificationSent)
    {
      if(isEmailNotificationEnabled)  Blynk.email("Blynk: {DEVICE_NAME} Buzzer", "Buzzer Activated.");
      if(isPushNotificationEnabled)   Blynk.notify("{DEVICE_NAME} Buzzer Activated.");

      isNotificationSent = true;
    }
  }
}

//<===================== BUZZER FUNCTIONS =====================>
void buzzer()
{
  Blynk.syncVirtual(VPIN_BUZZER_MANUAL, VPIN_ALARM);
  if(activateBuzzer && isSystemEnabled)
  {
    digitalWrite(buzzerPin, HIGH);
  }
  else
  {
    digitalWrite(buzzerPin, LOW);

    // Lower the flags to enable sending log and notification after
    // turning to OFF state.
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
  Blynk.begin(auth, ssid, pass, IPAddress(192,168,0,0), 8080);

  // Clock sync interval in seconds (10 minutes)
  setSyncInterval(10 * 60);

  // Set buzzer pin as OUTPUT and start in OFF state
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW);

  timer.setInterval(1000L, send_log);
  timer.setInterval(5000L, send_notification);
  timer.setInterval(500L, buzzer);
}

void loop()
{
  Blynk.run();
  timer.run();
}
