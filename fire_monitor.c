#include "fire_monitor.h"
#include "mq-2.h"
#include "ds18b20.h"
#include "usart.h"
#include "bsp_motor_iic.h"

extern uint8_t times;

void FireMonitor_Init(void)
{
    MQ2_Init();
    DS18B20_Init();
}

void FireMonitor_Process(void)
{

    float smoke = MQ2_GetConcentration();
    float temp = DS18B20_GetTemperature();
    uint8_t fire_alarm = 0;
    if (temp >= TEMP_THRESHOLD) {
        fire_alarm = 1;
    }

    Read_10_Enconder();  

    printf("%d %d %d %d %d\r\n",
           fire_alarm,
           Encoder_Offset[0],
           Encoder_Offset[1],
           Encoder_Offset[2],
           Encoder_Offset[3]);
}