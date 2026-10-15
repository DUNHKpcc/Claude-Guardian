#!/usr/bin/env python3
"""Offline full interview adapter. No network, native actions, or implicit saving."""
import argparse
import json
import sys
import guardian
import interview_flow as flow


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='strict')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', help='Previously explicitly saved private state JSON')
    parser.add_argument('--target-ref', help='Target alias; must match when resuming')
    parser.add_argument('--account-ref', help='Account alias; must match when resuming')
    parser.add_argument('--answer-file', help='Local JSON: question_id, value, state, source alias')
    parser.add_argument('--context-file', help='Explicit host routing facts; not action permission')
    parser.add_argument('--output', help='Opt-in private state file; never overwrites')
    args=parser.parse_args(argv)
    try:
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
            if set(item)-{'question_id','value','state','source'}:
                raise flow.InterviewError('Invalid answer envelope')
            state=flow.record_fact(state,item['question_id'],item.get('value'),
                state_name=item.get('state','reported'),source=item.get('source','user:current-turn'))
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
        print(json.dumps(output,ensure_ascii=False,indent=2))
        return 0
    except (flow.InterviewError,guardian.GuardianError,KeyError,TypeError,ValueError):
        print(json.dumps({'status':'blocked','code':'INVALID_OR_UNAUTHORIZED_INTERVIEW_IO','action_executed':False}))
        return 2
    except KeyboardInterrupt:
        print(json.dumps({'status':'cancelled','action_executed':False}))
        return 3

if __name__=='__main__':
    raise SystemExit(main())
