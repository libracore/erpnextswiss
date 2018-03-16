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
    mysql "$1" < viewVAT_301.sql
    mysql "$1" < viewVAT_311.sql   
    mysql "$1" < viewVAT_321.sql
    mysql "$1" < viewVAT_331.sql
    mysql "$1" < viewVAT_341.sql
    mysql "$1" < viewVAT_381.sql
    mysql "$1" < viewVAT_400.sql                     
    mysql "$1" < viewVAT_405.sql    
  else
    echo "Please provide the database schema name as first parameter"
fi
