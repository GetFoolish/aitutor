import argparse
from src.dash_system.workflow import CurriculumWorkflow
from src.dash_system.skills_cache import init_skills_cache


def main():
    parser = argparse.ArgumentParser(description="Curriculum workflow CLI")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("propose")
    p.add_argument("skill_id")
    p.add_argument("name")
    p.add_argument("learning_path")
    p.add_argument("difficulty", type=float)
    p.add_argument("forgetting_rate", type=float)

    sub.add_parser("list")

    a = sub.add_parser("approve")
    a.add_argument("skill_id")

    r = sub.add_parser("refresh")

    args = parser.parse_args()
    wf = CurriculumWorkflow()

    if args.cmd == "propose":
        wf.propose_skill({
            "_id": args.skill_id,
            "name": args.name,
            "learning_path": args.learning_path,
            "difficulty": args.difficulty,
            "forgetting_rate": args.forgetting_rate,
        })
        print("proposed", args.skill_id)
    elif args.cmd == "list":
        pending = wf.list_pending()
        print(pending)
    elif args.cmd == "approve":
        ok = wf.approve_skill(args.skill_id)
        print("approved" if ok else "not-found")
    elif args.cmd == "refresh":
        n = init_skills_cache()
        print("skills cache size:", n)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
