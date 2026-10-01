/*     stm32 and linuxcnc ortak udpcompenet.h uygun olur        */



// 0xfff.f     32 bit tanımlamalı float  sayı 24.8 fixed point bilmiyorum
//int64_t   analog;
struct OZEL  {
    float   veriA;
    float   veriB;
    float   veriC;
    float controlx;
    float control;
} ozel;// = { 0.0, 0.0, 0, 0  };


 

struct FB {

    uint16_t control;
    uint16_t io;
    int32_t pos[4];
    float   vel[4];
    
} fb ;//= {  0, 0, 0, 0, 0, 0.0, 0.0, 0.0 };

struct CMD {

    uint16_t control;
    uint16_t io;
    int32_t pos[4];
    float   vel[4];
  
} cmd ;//= {  0, 0, 0, 0, 0.0, 0.0, 0.0 };
