#include "cmd_handler.h"
#include "usart.h"
#include "bsp_motor_iic.h"

#define DEFAULT_SPEED 300   

static int16_t current_speed = DEFAULT_SPEED;

void process_serial_commands(void)
{
    if (USART_GetFlagStatus(USART1, USART_FLAG_RXNE) != RESET)
    {
        uint8_t cmd = USART_ReceiveData(USART1);
        
       
        if (cmd == '1') {
            current_speed = 100;
            printf("Speed set to 100\n");
        }
        else if (cmd == '2') {
            current_speed = 200;
            printf("Speed set to 200\n");
        }
        else if (cmd == '3') {
            current_speed = 300;
            printf("Speed set to 300\n");
        }
        else {
            
            switch (cmd)
            {
                case 'F':   
                    control_speed(current_speed, current_speed, current_speed, current_speed);
                    break;
                case 'B':   
                    control_speed(-current_speed, -current_speed, -current_speed, -current_speed);
                    break;
                case 'L':   
                    control_speed(-current_speed, -current_speed, current_speed, current_speed);
                    break;
                case 'R':   
                    control_speed(current_speed, current_speed, -current_speed, -current_speed);
                    break;
                case 'S':   
                    control_speed(0, 0, 0, 0);
                    break;
                default:
                    break;
            }
        }
    }
}
