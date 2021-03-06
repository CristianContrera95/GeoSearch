

venv_exist=$(ls | grep "venv" | wc -l)
cred_exist=$(ls | grep "creds" | wc -l)


if [ "$1" == "create" ];
then
	if [ $(( $venv_exist )) == 1 ];
	then
		rm -r venv
	fi
        if [ $(( $cred_exist )) == 1 ]:
        then
                mkdir creds
        fi
        virtualenv -p python3 venv
	source venv/bin/activate
	pip install -r requeriments.txt
	deactivate
fi

if [ "$1" == "run" ];
then
	if [ $(( $venv_exist )) == 1 ];
	then
		source venv/bin/activate
		python geosearch.py $2 $3 $4 $5 $6 $7
		deactivate
	else
		printf "Must first run:\n\t./geosearch.sh create\n"
	fi
fi

if [ "$1" == "help" ];
then
	if [ $(( $venv_exist )) == 1 ];
	then
		source venv/bin/activate
		python geosearch.py $1
		deactivate
	else
		printf "Must first run:\n\t./geosearch.sh create\n"
	fi	
fi
