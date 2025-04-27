import pandas as pd
from fasthtml.common import *

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.frontend.utils.extract import get_leader_extended
from op_tcg.frontend.utils.launch import init_load_data

app, rt, todos, Todo = fast_app(
    'data/todos.db',
    hdrs=[Style(':root { --pico-font-size: 100%; }')],
    id=int, title=str, done=bool, pk='id')

id_curr = 'current-todo'


def tid(id):
    return f'todo-{id}'

def init_data():
    init_load_data()
    meta_format: MetaFormat = MetaFormat.OP10
    meta_format_region: MetaFormatRegion = MetaFormatRegion.ALL
    only_official = True
    sort_by: LeaderboardSortBy = LeaderboardSortBy.DOMINANCE_SCORE

    display_name2df_col_name = {
        "Name": "name",
        LeaderboardSortBy.DOMINANCE_SCORE.value: "d_score",
        LeaderboardSortBy.TOURNAMENT_WINS.value: "tournament_wins",
        "Match Count": "total_matches",
        LeaderboardSortBy.WIN_RATE.value: "win_rate",
        LeaderboardSortBy.ELO.value: "elo",
    }
    # get data
    leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=meta_format_region)

    # drop None values
    required_values = ["elo", "win_rate", "total_matches", "only_official"]
    leader_extended_data: list[LeaderExtended] = list(
        filter(lambda x: all(getattr(x, v) is not None for v in required_values), leader_extended_data))


    if leader_extended_data:
        # display table.
        df_leader_extended = pd.DataFrame(
            [{**r.dict(), "color_hex_code": r.to_hex_color()} for r in leader_extended_data])

        fn_args = (df_leader_extended, meta_format, display_name2df_col_name, only_official)
        fn_kwargs = {"key": "leaderboard_table"}

    else:
        Div("Seems like the selected meta does not contain any matches")

@patch
def __ft__(self: Todo):
    show = AX(self.title, f'/todos/{self.id}', id_curr)
    edit = AX('edit', f'/edit/{self.id}', id_curr)
    dt = ' ✅' if self.done else ''
    return Li(show, dt, ' | ', edit, id=tid(self.id))


def mk_input(**kw): return Input(id="new-title", name="title", placeholder="New Todo", required=True, **kw)


@rt("/")
def get():
    init_data()
    add = Form(Group(mk_input(), Button("Add")),
               hx_post="/", target_id='todo-list', hx_swap="beforeend")
    card = Card(Ul(*todos(), id='todo-list'),
                header=add, footer=Div(id=id_curr)),
    title = 'Todo list'
    return Title(title), Main(H1(title), card, cls='container')


@rt("/todos/{id}")
def delete(id: int):
    todos.delete(id)
    return clear(id_curr)


@rt("/")
def post(todo: Todo):
    return todos.insert(todo), mk_input(hx_swap_oob='true')


@rt("/edit/{id}")
def get(id: int):
    res = Form(Group(Input(id="title"), Button("Save")),
               Hidden(id="id"), CheckboxX(id="done", label='Done'),
               hx_put="/", hx_swap="outerHTML", target_id=tid(id), id="edit")
    return fill_form(res, todos.get(id))


@rt("/")
def put(todo: Todo):
    return todos.upsert(todo), clear(id_curr)


@rt("/todos/{id}")
def get(id: int):
    todo = todos.get(id)
    btn = Button('delete', hx_delete=f'/todos/{todo.id}',
                 target_id=tid(todo.id), hx_swap="outerHTML")
    return Div(Div(todo.title), btn)


serve()
