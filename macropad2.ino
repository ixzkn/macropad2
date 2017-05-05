// For: 3.3v ProMicro
#include <Adafruit_NeoPixel.h>

// Parameter 1 = number of pixels in strip
// Parameter 2 = pin number (most are valid)
// Parameter 3 = pixel type flags, add together as needed:
//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
Adafruit_NeoPixel strip = Adafruit_NeoPixel(2, 6, NEO_GRB + NEO_KHZ800);

// use 50ms debounce time
#define DEBOUNCE_TICKS 50

// switch check rate
#define SWITCH_TICKS 100

// keys
#define KEYCOUNT 5

// lights
#define LIGHTCOUNT 2

// color channels per light (RGB)
#define CHANNEL_PER_LIGHT 3

// Maximum number of macros in one direction (up/down)
#define MAX_MACRO_SIZE 4

// Macro derives
#define FULL_MACRO_SIZE MAX_MACRO_SIZE*2
#define PROG_SIZE KEYCOUNT*FULL_MACRO_SIZE
#define MACRO_END 132

// Key input / debounce
const word keymap[KEYCOUNT] = {3,2,0,1,7}; // map from pin to key number
word keytick[KEYCOUNT];  // last recorded tick time of keypress
word lastval[KEYCOUNT];  // last value of key press (0 - PRESSED, 1 - NOT PRESSED)
word lastread[KEYCOUNT]; // last time keypress was checked 

// Switch input / debounce
const word switchPin = 10;
word lastSwitchState = 0;
long lastSwitchTime = 0;

// keyboard control
boolean keyboardMode = false;
struct{
  word down[MAX_MACRO_SIZE];
  word up[MAX_MACRO_SIZE];
} cmdmap[KEYCOUNT] = {
  { {'z', MACRO_END, MACRO_END, MACRO_END}, {'z', MACRO_END, MACRO_END, MACRO_END} },
  { {'x', MACRO_END, MACRO_END, MACRO_END}, {'x', MACRO_END, MACRO_END, MACRO_END} },
  { {'z', MACRO_END, MACRO_END, MACRO_END}, {'z', MACRO_END, MACRO_END, MACRO_END} },
  { {'x', MACRO_END, MACRO_END, MACRO_END}, {'x', MACRO_END, MACRO_END, MACRO_END} },
  { {'x', MACRO_END, MACRO_END, MACRO_END}, {'x', MACRO_END, MACRO_END, MACRO_END} }
};

// For async reading of serial inputs
int serialState = 0;
int lightTarget = 0;
int lightTargetColor[CHANNEL_PER_LIGHT] = {0,0,0};

void KeyInterHandler(word key)
{
  word valueNow = digitalRead(keymap[key]);
  word now = (word)millis();
  if((now - keytick[key]) > DEBOUNCE_TICKS && (lastval[key] != valueNow))
  {
    keytick[key] = now;
    lastval[key] = valueNow;
  }
}

void KeyPress0() {
  KeyInterHandler(0);
}
void KeyPress1() {
  KeyInterHandler(1);
}
void KeyPress2() {
  KeyInterHandler(2);
}
void KeyPress3() {
  KeyInterHandler(3);
}
void KeyPress4() {
  KeyInterHandler(4);
}

// returns true if key pressed
boolean KeyChanged(word key) {
  // second part of OR is for overflow
  if((lastread[key] < keytick[key] || (lastread[key] - DEBOUNCE_TICKS) > keytick[key]) && (word)millis()-keytick[key] < 50)
  {
    lastread[key] = keytick[key];
    return true;
  }
  return false;
}

boolean KeyDown(word key) {
  return lastval[key] == 0;
}

void setup() {
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'

  Serial.begin(115200);

  for(int x=0; x < KEYCOUNT; x++)
  {
    pinMode(keymap[x], INPUT_PULLUP);
    keytick[x] = 0;
    lastread[x] = millis() + DEBOUNCE_TICKS;
    lastval[x] = 1;
  }

  pinMode(switchPin, INPUT_PULLUP);
  lastSwitchState = digitalRead(switchPin);
  lastSwitchTime = millis() + DEBOUNCE_TICKS;

  attachInterrupt(0,KeyPress0,CHANGE);
  attachInterrupt(1,KeyPress1,CHANGE);
  attachInterrupt(2,KeyPress2,CHANGE);
  attachInterrupt(3,KeyPress3,CHANGE);
  attachInterrupt(4,KeyPress4,CHANGE);
}

void BlankLights()
{
  strip.setPixelColor(0,0,0,0);
  strip.setPixelColor(1,0,0,0);
  strip.show();
}

void KeyModeLights()
{
  strip.setPixelColor(0,0,5,11);
  strip.setPixelColor(1,11,6,9);
  strip.show();
}

void EnterKeyMode()
{
  KeyModeLights();
  keyboardMode = true;
  Serial.println("kbd");
  Keyboard.begin();
}

void ExitKeyMode()
{
  BlankLights();
  keyboardMode = false;
  Keyboard.end();
  Serial.println("nkb");
}

void loopKeyboardMode()
{
  for(int x=0; x < KEYCOUNT; x++)
  {
    if(KeyChanged(x))
    {
      if(KeyDown(x))
      {
        for(int i=0; i<MAX_MACRO_SIZE; i++)
        {
          word key = cmdmap[x].down[i];
          if(key == MACRO_END) break;
          Keyboard.press(key);
        }
      }
      else
      {
        for(int i=0; i<MAX_MACRO_SIZE; i++)
        {
          word key = cmdmap[x].up[i];
          if(key == MACRO_END) break;
          Keyboard.release(key);
        }
      }
    }
  }
}

void loopControllerMode()
{
  for(int x=0; x < KEYCOUNT; x++)
  {
    if(KeyChanged(x))
    {
      Serial.print(x);
      Serial.print("-");
      Serial.print(KeyDown(x));
      Serial.print("\r\n");
    }
  }
}

void loopHandleInput()
{
  int inByte = Serial.read();
  if(serialState == 0)
  {
    if(inByte == 't')
    {
      Serial.print(millis());
      Serial.print("\r\n");
    }
    else if(inByte == '0')
    {
      serialState = CHANNEL_PER_LIGHT;
      lightTarget = 0;
    }
    else if(inByte == '1')
    {
      serialState = CHANNEL_PER_LIGHT;
      lightTarget = 1;
    }
    else if(inByte == 'k')
    {
      EnterKeyMode();
    }
    else if(inByte == 'x')
    {
      ExitKeyMode();
    }
    else if(inByte == 'm')
    {
      Serial.print(digitalRead(10));
      Serial.print("\r\n");
    }
    else if(inByte == 'p')
    {
      serialState = CHANNEL_PER_LIGHT+PROG_SIZE;
    }
    else if(inByte == 'g')
    {
      for(int x=0; x<KEYCOUNT; x++)
      {
        for(int i=0; i<MAX_MACRO_SIZE; i++)
        {
          word key = cmdmap[x].down[i];
          if(key == MACRO_END) break;
          Serial.print(key);  
          Serial.print(",");
        }
        Serial.print("-");
        for(int i=0; i<MAX_MACRO_SIZE; i++)
        {
          word key = cmdmap[x].up[i];
          if(key == MACRO_END) break;
          Serial.print(key);  
          Serial.print(",");
        }
        Serial.print(":");
      }
      Serial.print("\r\n");
    }
  }
  else
  {
    serialState--;
    if(serialState >= CHANNEL_PER_LIGHT)
    {
      // keymap set mode: 42...3
      word key = (serialState - CHANNEL_PER_LIGHT) >> 3;
      word pos = (serialState - CHANNEL_PER_LIGHT) - (key << 3);
      if(pos >= MAX_MACRO_SIZE)
      {
        cmdmap[key].up[pos-MAX_MACRO_SIZE] = inByte;
      }
      else
      {
        cmdmap[key].down[pos] = inByte;
      }
      if(serialState == CHANNEL_PER_LIGHT)
      {
        serialState = 0;
      }
    }
    else
    {
      // light set mode: 2, 1, 0
      lightTargetColor[serialState] = inByte;
      if(serialState == 0)
      {
        strip.setPixelColor(lightTarget, lightTargetColor[0], lightTargetColor[1], lightTargetColor[2]);
        strip.show();
      }
    }
  }
}

void loopSwitchCheck()
{
  long now = millis();
  if(now - lastSwitchTime > SWITCH_TICKS)
  {
    // check switch state:
    word switchState = digitalRead(switchPin);
    lastSwitchTime = now;
    if(lastSwitchState != switchState)
    {
      lastSwitchState = switchState;
      if(keyboardMode)
      {
        ExitKeyMode();
      }
      else
      {
        EnterKeyMode();
      }
    }
  }
}

void loop() {
  if (Serial.available() > 0) {
    loopHandleInput();
  }
  if(keyboardMode)
  {
    loopKeyboardMode();
  }
  else
  {
    loopControllerMode();
  }
  loopSwitchCheck();
}

