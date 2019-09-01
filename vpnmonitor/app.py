import time
from typing import Union

from pyroute2 import IPDB, IPRoute
from pyroute2.ipdb.main import Watchdog

print('Inicializando...')


def prompt_sudo():
    import os, subprocess
    user_uid = os.geteuid()
    if user_uid != 0:
        return subprocess.check_call("sudo -v -p '%s'" % "[SUDO] senha para %u:", shell=True)
    return user_uid


print('Verificando permissoes de root')
if prompt_sudo() != 0:
    print('Saindo! Necessario permissoes de root')
    exit()


def delete_route(origin: str, route: object):
    print(origin + 'Deletando rota de rede ', route)
    from pyroute2 import IPRoute
    iproute_del: Union[IPRoute, IPRoute, IPRoute] = IPRoute()
    iproute_del.route("del", table=route.get("table"),
                             family=route.get("family"),
                             scope=route.get("scope"),
                             dst_len=route.get("dst_len"),
                             src_len=route.get("src_len"),
                             tos=route.get("tos"),
                             flags=route.get("flags"),
                             type=route.get("type"),
                             proto=route.get("proto"),
                             attrs=route.get("attrs"))
    iproute_del.close()


def watchdog_callback(ipdb: object, route: object, action: object):
    if action == 'RTM_NEWROUTE':
        for attrs in route.get("attrs", []):
            if attrs[0] == 'RTA_PRIORITY' and attrs[1] > 15000:
                print('[watchdog] Encontrado rota de rede com erro')
                delete_route('[watchdog] ', route)


print('Verificando rotas de rede')
iproute: Union[IPRoute, IPRoute, IPRoute] = IPRoute()
routes = iproute.get_routes()

for idx in range(len(routes)):
    for attrs in routes[idx].get('attrs', []):
        if attrs[0] == 'RTA_PRIORITY' and attrs[1] > 15000:
            print('Encontrado rota de rede com erro')
            delete_route('', routes[idx])

iproute.close()

print('Inicializando watchdog')
ipdb: IPDB = IPDB()
watchdog: Watchdog = ipdb.watchdog()
watchdog.wait()

print('Registrando callback')
callback: int = ipdb.register_callback(watchdog_callback)

print('Monitorando rotas de rede... <[CTRL] + C> para encerrar!')
while True:
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print('Des-registrando callback')
        ipdb.unregister_callback(callback)
        print('Finalizando watchdog')
        ipdb.release()
        break

print('Terminando... Laterz!')
