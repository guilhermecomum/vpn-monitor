# vpnmonitor

Dependencias do SO:
```
sudo apt install python3 python3-pip
```

Python packages:
```
pip3 install -r requirements.txt
```

Para executar o monitor:
```
sudo python3 vpnmonitor/app.py
```

Para monitorar as rotas pelo SO:
``` 
clear; while true; do printf "\033[1;1H"; route -n; sleep 1; clear; done

```
## TODO

- Habilitar logger
- Criar self installer
- Rodar como service do SO
