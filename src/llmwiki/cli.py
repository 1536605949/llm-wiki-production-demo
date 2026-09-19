from __future__ import annotations
import argparse, json
from .service import LLMWikiService

def dump(x):
    print(json.dumps(x, ensure_ascii=False, indent=2))

def main():
    p = argparse.ArgumentParser(prog="llmwiki", description="LLM-Wiki production-shaped demo")
    sub = p.add_subparsers(dest="cmd", required=True)

    a=sub.add_parser("init"); a.add_argument("workspace")
    a=sub.add_parser("status"); a.add_argument("workspace")
    a=sub.add_parser("add"); a.add_argument("workspace"); a.add_argument("source")
    a=sub.add_parser("ingest"); a.add_argument("workspace"); a.add_argument("raw_path")
    a=sub.add_parser("query"); a.add_argument("workspace"); a.add_argument("question"); a.add_argument("--save", action="store_true")
    a=sub.add_parser("lint"); a.add_argument("workspace"); a.add_argument("--semantic", action="store_true")
    a=sub.add_parser("reindex"); a.add_argument("workspace")
    a=sub.add_parser("serve"); a.add_argument("workspace"); a.add_argument("--host", default="127.0.0.1"); a.add_argument("--port", type=int, default=8000)

    args=p.parse_args()
    svc=LLMWikiService(args.workspace)
    if args.cmd=="init": dump(svc.init())
    elif args.cmd=="status": dump(svc.status())
    elif args.cmd=="add": dump({"path":"raw/"+svc.ws.add_source(args.source).name})
    elif args.cmd=="ingest": dump(svc.ingest(args.raw_path))
    elif args.cmd=="query": dump(svc.query(args.question, args.save))
    elif args.cmd=="lint": dump(svc.lint(args.semantic))
    elif args.cmd=="reindex": dump(svc.reindex())
    elif args.cmd=="serve":
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(args.workspace), host=args.host, port=args.port)

if __name__ == "__main__":
    main()
