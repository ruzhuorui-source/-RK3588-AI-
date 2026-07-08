#include "mq-2.h"
#include "stm32f10x_adc.h"
#include "stm32f10x_rcc.h"
#include "stm32f10x_gpio.h"

void MQ2_Init(void) {
    GPIO_InitTypeDef GPIO_InitStruct;
    ADC_InitTypeDef ADC_InitStruct;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_ADC1, ENABLE);

    GPIO_InitStruct.GPIO_Pin = MQ2_ADC_GPIO_PIN;
    GPIO_InitStruct.GPIO_Mode = GPIO_Mode_AIN;
    GPIO_Init(MQ2_ADC_GPIO_PORT, &GPIO_InitStruct);

    ADC_DeInit(MQ2_ADC);
    ADC_InitStruct.ADC_Mode = ADC_Mode_Independent;
    ADC_InitStruct.ADC_ScanConvMode = DISABLE;
    ADC_InitStruct.ADC_ContinuousConvMode = DISABLE;
    ADC_InitStruct.ADC_ExternalTrigConv = ADC_ExternalTrigConv_None;
    ADC_InitStruct.ADC_DataAlign = ADC_DataAlign_Right;
    ADC_InitStruct.ADC_NbrOfChannel = 1;
    ADC_Init(MQ2_ADC, &ADC_InitStruct);

    ADC_Cmd(MQ2_ADC, ENABLE);
    ADC_ResetCalibration(MQ2_ADC);
    while(ADC_GetResetCalibrationStatus(MQ2_ADC));
    ADC_StartCalibration(MQ2_ADC);
    while(ADC_GetCalibrationStatus(MQ2_ADC));

    ADC_RegularChannelConfig(MQ2_ADC, MQ2_ADC_CHANNEL, 1, ADC_SampleTime_55Cycles5);
}

uint16_t MQ2_ReadRaw(void) {
    ADC_SoftwareStartConvCmd(MQ2_ADC, ENABLE);
    while(ADC_GetFlagStatus(MQ2_ADC, ADC_FLAG_EOC) == RESET);
    return ADC_GetConversionValue(MQ2_ADC);
}

float MQ2_GetVoltage(void) {
    return (float)MQ2_ReadRaw() * 3.3f / 4096.0f;
}

float MQ2_GetConcentration(void) {
    float v = MQ2_GetVoltage();
    float conc = (v - 0.1f) / 3.2f * 100.0f;
    if(conc < 0) conc = 0;
    if(conc > 100) conc = 100;
    return conc;
}
