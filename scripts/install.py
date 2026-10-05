import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description='Install the independent OrangeJuice service and optional bridge');p.add_argument('--framework-root');p.add_argument('--plugins-directory');p.add_argument('--framework-configs-directory');p.add_argument('--port',type=int,default=15082);p.add_argument('--public-url');p.add_argument('--install-deps',action='store_true');p.add_argument('--systemd',action='store_true');p.add_argument('--yunzai-bridge',action='store_true');args=p.parse_args()
if not 1024<=args.port<=65535:raise SystemExit('Choose a port from 1024 to 65535')
if args.install_deps:subprocess.run([sys.executable,'-m','pip','install','-r',str(root/'requirements.txt')],check=True)
try:import yaml,psutil
except ImportError:raise SystemExit('Install requirements in the Python environment that runs the service')
config=root/'config/local.json'
settings=json.loads((root/'config/example.json').read_text(encoding='utf-8'))
framework=Path(args.framework_root or root/'workspace').resolve();plugins=Path(args.plugins_directory or framework/'plugins').resolve();plugins.mkdir(parents=True,exist_ok=True)
settings.update(host='127.0.0.1',port=args.port,publicUrl=args.public_url or 'http://127.0.0.1:'+str(args.port),frameworkRoot=str(framework),pluginsDirectory=str(plugins),bridgeDirectory=str(root/'data/bridge'),runtimeFile=str(root/'data/bridge/runtime.json'))
if args.framework_configs_directory:
    configs=Path(args.framework_configs_directory).resolve()
    if not configs.is_relative_to(framework):raise SystemExit('Framework configuration directory must be inside framework-root; register external files using extraConfigs')
    settings['frameworkConfigsDirectory']=str(configs)
if args.yunzai_bridge:
    if config.exists():raise SystemExit('Existing local config found; add bridge manually using docs/DEPLOYMENT.md so IPC paths stay consistent')
    if not (framework/'lib/plugins/loader.js').exists():raise SystemExit('Yunzai bridge requires a compatible lib/plugins/loader.js')
    bridge=plugins/'OrangeJuice-Plugin'
    if bridge.exists():raise SystemExit('Bridge directory already exists; existing files were not overwritten')
    shutil.copytree(root/'integrations/yunzai',bridge)
    ipc=framework/'data/orangejuice';ipc.mkdir(parents=True,exist_ok=True);settings.update(frameworkName='Yunzai V3',bridgeDirectory=str(ipc),runtimeFile=str(ipc/'runtime.json'))
    (bridge/'config').mkdir(exist_ok=True);(bridge/'config/local.json').write_text(json.dumps({'publicUrl':settings['publicUrl'],'ipcDirectory':'data/orangejuice'},indent=2))
if not config.exists():config.write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8');os.chmod(config,0o600)
else:print('Existing local config retained')
if args.systemd:
    if sys.platform!='linux' or os.geteuid()!=0:raise SystemExit('--systemd requires Linux root')
    if any(c in str(root)+sys.executable for c in '\n\r"'):raise SystemExit('Unsupported service path')
    unit=Path('/etc/systemd/system/orangejuice.service')
    if unit.exists():raise SystemExit('Existing systemd unit retained; update manually')
    unit.write_text('[Unit]\nDescription=OrangeJuice independent control center\nAfter=network.target\n\n[Service]\nType=simple\nWorkingDirectory='+str(root)+'\nExecStart='+sys.executable+' -m orangejuice.server serve --config '+str(config)+' --data '+str(root/'data')+'\nRestart=on-failure\nUMask=0077\nNoNewPrivileges=true\nPrivateTmp=true\n\n[Install]\nWantedBy=multi-user.target\n')
    subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','enable','--now','orangejuice'],check=True)
print('Ready. Start: python -m orangejuice.server serve --config config/local.json --data data')
print('First owner password: data/bootstrap.txt; or use the ticket command after service start.')
