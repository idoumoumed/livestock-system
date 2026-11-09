#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

// بيانات شبكة الواي فاي
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// روابط السيرفر على Render
const char* serverSensorUrl = "https://livestock-system-byvb.onrender.com/api/sensor_update";
const char* serverImageUrl  = "https://livestock-system-byvb.onrender.com/api/upload_image";

// إعدادات أطراف الكاميرا لـ ESP32-CAM (AI-Thinker)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  if(psramFound()){
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  } else {
    config.frame_size = FRAMESIZE_QQVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }
  
  esp_camera_init(&config);
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  
  setupCamera();
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    
    // 1. إرسال بيانات الحساسات (درجة الحرارة)
    {
      HTTPClient http;
      http.begin(serverSensorUrl);
      http.addHeader("Content-Type", "application/json");
      
      float temperature = 29.1; // ضع قراءة الحساس الحقيقي هنا لاحقاً
      String jsonPayload = "{\"device_id\":\"CAM_CAMEL_01\",\"temperature\":" + String(temperature) + "}";
      
      int respCode = http.POST(jsonPayload);
      if (respCode > 0) {
        Serial.println("Sensor data sent!");
      }
      http.end();
    }

    // 2. التقاط صورة الكاميرا الحية ورفعها للسيرفر
    {
      camera_fb_t * fb = esp_camera_fb_get();
      if (fb) {
        HTTPClient httpImg;
        httpImg.begin(serverImageUrl);
        
        int imgRespCode = httpImg.sendRequest("POST", fb->buf, fb->len);
        if (imgRespCode > 0) {
          Serial.println("Live frame uploaded successfully!");
        }
        
        esp_camera_fb_return(fb);
        httpImg.end();
      } else {
        Serial.println("Camera capture failed!");
      }
    }

  } else {
    Serial.println("WiFi Disconnected");
  }
  
  // تحديث البيانات والصورة كل 5 ثوانٍ بانتظام
  delay(5000); 
}
