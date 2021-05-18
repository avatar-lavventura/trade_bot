#!/usr/bin/env python3

from colorama import Fore, Style, init

init(autoreset=True)
print(f"{Fore.YELLOW}{Style.BRIGHT}some red tex")
print("automatically back to default color again")
