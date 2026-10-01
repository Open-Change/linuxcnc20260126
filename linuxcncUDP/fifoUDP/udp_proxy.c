// udp_proxy.c
// Derleme: gcc -O2 -Wall -o udp_proxy udp_proxy.c

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/stat.h>

#define FIFO_PATH "/var/run/udp_enc.fifo"
#define PORT 5000
#define BUF_SIZE 128

int main(void)
{
    int sockfd;
    int fifo_fd;
    struct sockaddr_in addr;
    char buffer[BUF_SIZE];

    /* ---------- FIFO OLUŞTUR ---------- */
    if (access(FIFO_PATH, F_OK) != 0) {
        if (mkfifo(FIFO_PATH, 0666) < 0) {
            perror("mkfifo");
            return 1;
        }
    }

    printf("[udp_proxy] FIFO hazır: %s\n", FIFO_PATH);

    /* ---------- FIFO OKUYUCU BEKLE ---------- */
    printf("[udp_proxy] FIFO okuyucu bekleniyor...\n");
    while ((fifo_fd = open(FIFO_PATH, O_WRONLY | O_NONBLOCK)) < 0) {
        if (errno != ENXIO) {
            perror("open fifo");
            return 1;
        }
        usleep(100000);  // 100 ms
    }

    printf("[udp_proxy] FIFO bağlı\n");

    /* ---------- UDP SOCKET ---------- */
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        perror("socket");
        return 1;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_port        = htons(PORT);
    addr.sin_addr.s_addr = htonl(INADDR_ANY);

    if (bind(sockfd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        return 1;
    }

    printf("[udp_proxy] UDP dinleniyor: port %d\n", PORT);

    /* ---------- ANA DÖNGÜ ---------- */
    while (1) {
        ssize_t n = recvfrom(sockfd, buffer, BUF_SIZE - 2, 0, NULL, NULL);
        if (n <= 0)
            continue;

        /* newline ekle */
        buffer[n++] = '\n';
        buffer[n]   = '\0';

        /* FIFO'ya yaz */
        ssize_t w = write(fifo_fd, buffer, n);
        if (w < 0) {
            perror("write fifo");
        }
    }

    close(fifo_fd);
    close(sockfd);
    return 0;
}


// gcc -o udp_proxy udp_proxy.c

/*FIFO Dizini Oluştur (Yalnızca bir kez)
bash

derleme 
gcc -o udp_proxy udp_proxy.c

* 
* 
ls -l udp_proxy
chmod +x udp_proxy
ls -l udp_proxy
* 
# Şimdi
sudo mkdir -p /var/run

chmod +x run_udp_proxy.sh
./run_udp_proxy.sh

chmod +x stop_udp_proxy.sh
./stop_udp_proxy.sh
 
ps aux | grep udp_proxy

 
*/
