#!/usr/bin/env python3
"""Offline full interview adapter. No network, native actions, or implicit saving."""
import argparse
import json
import sys
import guardian
import interview_flow as flow


class _PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default diagnostics reproduce unknown options and values.
        # The structured failure must not contain any of those private inputs.
        raise flow.InterviewError('Invalid interview command arguments') from None

    def _print_message(self, message, file=None):
        # argparse otherwise ignores write failures and can claim --help worked.
        if message:
            stream = file if file is not None else sys.stderr
            stream.write(message)
            stream.flush()


def _emit_result(result, *, indent=None):
    try:
        print(json.dumps(result, ensure_ascii=False, indent=indent), flush=True)
        return True
    except (OSError, ValueError):
        # Never report successful delivery or expose a raw stream error. stderr
        # may also be unavailable; the nonzero exit remains authoritative then.
        try:
            print(json.dumps({'status': 'blocked', 'code': 'INTERVIEW_OUTPUT_FAILED',
                              'action_executed': False, 'saved': result.get('saved', False)}),
                  file=sys.stderr, flush=True)
        except (OSError, ValueError):
            pass
        return False


def main(argv=None):
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='strict')
        parser=_PrivateArgumentParser(prog='interview_cli.py', description=__doc__)
        parser.add_argument('--input', help='Previously explicitly saved private state JSON')
        parser.add_argument('--target-ref', help='Target alias; must match when resuming')
        parser.add_argument('--account-ref', help='Account alias; must match when resuming')
        parser.add_argument('--answer-file', help='Local JSON: one question_id/value/state/source answer, or {"answers": [same answer objects]} from one reply')
        parser.add_argument('--context-file', help='Explicit host routing facts; not action permission')
        parser.add_argument('--output', help='Opt-in private state file; never overwrites')
        args=parser.parse_args(argv)
        if args.input:
            state=flow.loads_state(json.dumps(guardian.load_json(args.input)))
            if ((args.target_ref is not None and args.target_ref != state['target_alias']) or
                    (args.account_ref is not None and args.account_ref != state['account_alias'])):
                raise flow.InterviewError('Explicit resume target or account mismatch')
        else:
            state=flow.new_state(args.target_ref if args.target_ref is not None else 'target-unconfirmed',
                                 args.account_ref if args.account_ref is not None else 'account-unconfirmed')
        if args.context_file:
            state=flow.set_context(state,**guardian.load_json(args.context_file))
        if args.answer_file:
            item=guardian.load_json(args.answer_file)
            if isinstance(item,dict) and set(item)=={'answers'}:
                answers=item['answers']
            else:
                answers=[item]
            state=flow.record_facts(state,answers,source='user:current-turn')
        question=flow.next_question(state)
        # Asking is recorded only when a user response is absorbed. Merely rendering
        # CLI output must not lose the question if the host failed to deliver it.
        output={'schema_version':'guardian-intake-result/1','question':question,
                'assessment':flow.assessment(state),'contact_control':'host_authorization_required',
                'action_executed':False,'saved':False}
        # Provenance may contain private user text or identifiers. Preserve it in
        # explicitly saved private state, but do not reproduce it on stdout.
        subscription=output['assessment']['current_subscription']
        if subscription['source'] is not None:
            subscription['source']='private-source-retained'
        if args.output:
            serialized=flow.dumps_state(state,host_opt_in=True,scope='private_save')
            guardian.save_new(args.output,serialized+'\n')
            output['saved']=True
        return 0 if _emit_result(output, indent=2) else 2
    except (flow.InterviewError,guardian.GuardianError,KeyError,TypeError,ValueError,OSError):
        _emit_result({'status':'blocked','code':'INVALID_OR_UNAUTHORIZED_INTERVIEW_IO','action_executed':False})
        return 2
    except KeyboardInterrupt:
        _emit_result({'status':'cancelled','action_executed':False})
        return 3

if __name__=='__main__':
    code = main()
    try:
        sys.stdout.flush()
    except (OSError, ValueError):
        # Only the standalone process owns stdout. Close a failed buffered pipe
        # here so Python's shutdown flush cannot emit an unsanitized diagnostic.
        code = 2
        try:
            sys.stdout.close()
        except (OSError, ValueError):
            pass
    raise SystemExit(code)
