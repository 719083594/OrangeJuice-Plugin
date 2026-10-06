"""Build the optional bot's human command hints from the panel descriptions."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from orangejuice.feature_docs import RULES,EXTENSIONS
value={'builtins':{p+'::'+h:dict(title=t,command=c,description=d) for (p,h),(t,c,d) in RULES.items()},
       'extensions':{p:[dict(title=t,command=c,description=d) for t,c,d in rows] for p,rows in EXTENSIONS.items()}}
(root/'integrations/yunzai/command-docs.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
