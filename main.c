#include "AllHeader.h"
#include "cmd_handler.h" 
#include "fire_monitor.h" 

#define UPLOAD_DATA 2  
					 
                       
#define MOTOR_TYPE 2   
                     

uint8_t times = 0;




int main(void)
{	
	bsp_init();
	
	TIM3_Init();
	FireMonitor_Init();

	IIC_Motor_Init();
	printf("pelase wait...\r\n");
    control_pwm(0,0,0,0);
    delay_ms(100);

	
    #if MOTOR_TYPE == 1
	Set_motor_type(1);
	delay_ms(100);
	Set_Pluse_Phase(30);
	delay_ms(100);
	Set_Pluse_line(11);
	delay_ms(100);
	Set_Wheel_dis(67.00);
	delay_ms(100);
	Set_motor_deadzone(1900);
	delay_ms(100);
    
    #elif MOTOR_TYPE == 2
    Set_motor_type(2);
	delay_ms(100);
	Set_Pluse_Phase(20);
	delay_ms(100);
	Set_Pluse_line(13);
	delay_ms(100);
	Set_Wheel_dis(48.00);
	delay_ms(100);
	Set_motor_deadzone(1600);
	delay_ms(100);
    
    #elif MOTOR_TYPE == 3
    Set_motor_type(3);
	delay_ms(100);
	Set_Pluse_Phase(45);
	delay_ms(100);
	Set_Pluse_line(13);
	delay_ms(100);
	Set_Wheel_dis(68.00);
	delay_ms(100);
	Set_motor_deadzone(1250);
	delay_ms(100);
    
    #elif MOTOR_TYPE == 4
    Set_motor_type(4);
	delay_ms(100);
	Set_Pluse_Phase(48);
	delay_ms(100);
	Set_motor_deadzone(1000);
	delay_ms(100);
    
    #elif MOTOR_TYPE == 5
    Set_motor_type(1);
	delay_ms(100);
	Set_Pluse_Phase(40);
	delay_ms(100);
	Set_Pluse_line(11);
	delay_ms(100);
	Set_Wheel_dis(67.00);
	delay_ms(100);
	Set_motor_deadzone(1900);
	delay_ms(100);
    #endif

	while(1)
	{
		process_serial_commands();
		FireMonitor_Process();
		
	}
	
}
