"""Confirm an explicit tab close without guarding system quit requests."""

from kittens.tui.handler import result_handler


def main(args: list[str]) -> None:
    pass


@result_handler(no_ui=True)
def handle_result(args, answer, target_window_id, boss):
    window = boss.window_id_map.get(target_window_id)
    tab = window.tabref() if window is not None else None
    if tab is None:
        return

    # Repeated shortcuts focus the existing prompt instead of stacking dialogs.
    prompt = boss.window_id_map.get(tab.confirm_close_window_id)
    if prompt is not None and prompt in tab:
        tab.set_active_window(prompt)
        return

    prompt = boss.confirm(
        "Close this tab and all its terminal windows?",
        boss.handle_close_tab_confirmation,
        tab.id,
        window=window,
        confirm_on_accept=False,
        title="Close tab?",
    )
    tab.confirm_close_window_id = prompt.id
