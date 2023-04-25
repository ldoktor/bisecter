#!/bin/bash
[ $1 == 'FAILURE' ] && exit 135
[ $1 == 99 ] && [ $2 == 99 ] && [ $3 == 99 ] && exit 1
[ $2 -gt 3 ] && exit 125
[ $1 -lt 10 ] && [ $2 -lt 20 ] && [ $3 -lt 77 ] && exit 0
exit 1
