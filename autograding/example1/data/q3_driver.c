#include <stdio.h>
#include <string.h>
#include <math.h>

int main(int argc, char **argv)
{
    char rooms[] = {'b', 'c', 3, 8, 3, 'l', 'b', 'b', 'y'};
    int n = 9;
    find_bby(rooms, n);
    for (int i = 0; i < n; i++)
    {
        printf("%hu,", rooms[i]);
    }
    printf("\n");
}