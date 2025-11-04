#include <stdio.h>

int main() {
	__asm__ __volatile__("ud2");
	return 0;
}
