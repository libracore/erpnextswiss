#!/bin/bash

# this script will load all VAT tables to the designated database

if [ "$1" != "" ]
  then
    mysql "$1" < viewVAT_200.sql
    mysql "$1" < viewVAT_220.sql
    mysql "$1" < viewVAT_221.sql
    mysql "$1" < viewVAT_225.sql
    mysql "$1" < viewVAT_230.sql
    mysql "$1" < viewVAT_235.sql
    mysql "$1" < viewVAT_302.sql
    mysql "$1" < viewVAT_312.sql   
    mysql "$1" < viewVAT_322.sql
    mysql "$1" < viewVAT_332.sql
    mysql "$1" < viewVAT_342.sql
    mysql "$1" < viewVAT_382.sql
    mysql "$1" < viewVAT_400.sql                     
    mysql "$1" < viewVAT_405.sql    
  else
    echo "Please provide the database schema name as first parameter"
fi
