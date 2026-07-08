#ifndef __FIRE_MONITOR_H
#define __FIRE_MONITOR_H

#include "stm32f10x.h"

#define TEMP_THRESHOLD     32.0f   
#define SMOKE_THRESHOLD    30.0f   
#define MONITOR_PERIOD_MS  500     

void FireMonitor_Init(void);
void FireMonitor_Process(void);

#endif
