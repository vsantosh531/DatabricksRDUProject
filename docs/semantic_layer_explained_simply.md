# The Lemonade Stand Recipe Book

*A very simple story about what we built — for a 5-year-old, and maybe for
grown-ups too.*

---

## Once Upon a Time

You and your friends run a lemonade stand. You all sell lemonade, but every
friend makes it a little differently. One friend adds lots of sugar. Another
friend adds barely any. So when someone asks "how sweet is our lemonade?" —
nobody agrees! Everyone gives a different answer, and that's confusing.

*(Grown-up translation: different teams calculating the same business metric
differently — the "shadow metrics" problem.)*

---

## The One True Recipe Card

So you make **one recipe card** — just one — that says exactly: 4 lemons, 2
cups of sugar, 1 pitcher of water. Everyone uses this same card. Now when
anyone asks how sweet the lemonade is, everyone gives the *same* answer,
because everyone used the *same* card.

*(Grown-up translation: a Unity Catalog metric view — one governed
definition of a measure, like "median sale price," used everywhere.)*

---

## Two Recipe Boxes: Practice and Real

You get two boxes to keep your recipe cards in.

The **Practice Box** is where you try new recipes. Maybe you want to try
adding a little mint. That's okay — it's just practice, nobody's drinking it
yet.

The **Real Box** only holds recipes everyone has already tried and trusts.
That's what the actual lemonade stand uses to sell cups to customers.

*(Grown-up translation: `dev` and `prod` catalogs — a safe place to try
changes before they reach real users.)*

---

## The Grown-Up Taste Tester

Before a new recipe card can move from the Practice Box into the Real Box,
a grown-up helper tastes it first. They check: does it taste like it's
supposed to? Is it written clearly? Only after the grown-up says "yes, this
is good" does the card get a little gold star and move into the Real Box.

*(Grown-up translation: the CI/CD pipeline — parity tests, smoke tests, and
a required approval before anything deploys to prod.)*

---

## The Recipe Keeper Badge

Not everyone gets to put new cards in the Real Box — only whoever is
wearing the special **Recipe Keeper badge** can do that. Your friends who
sell lemonade at the stand can *read* the recipe card anytime they want, but
they can't go rummage through the raw lemons and sugar bags themselves and
make something up.

*(Grown-up translation: access control — a scoped identity deploys the
metric view; consumers get `SELECT` on the view, never direct access to the
raw gold tables.)*

---

## Ask the Genie

There's a friendly genie who lives near the stand. If you ask the genie
"how much lemonade did we sell today?", the genie looks at the recipe card
and tells you the answer right away — you don't have to do any counting or
math yourself.

*(Grown-up translation: a Genie space — ask a natural-language question, get
an answer computed from the governed metric view.)*

---

## The Little Notebook by the Door

There's a notebook taped by the recipe box. Every single time someone opens
the box and looks at a card, they write down their name and what time it
was. That way, you always know who looked at what, and you can tell if a
recipe card isn't being used by anyone anymore.

*(Grown-up translation: usage tracking via system tables — `access.audit`
and `query.history` — who queries what metric view, and when.)*

---

## The Lemon Counting Jar

You only have so many lemons this week. So you keep a jar where you drop in
a little pebble every time you use a lemon. If the jar starts filling up
fast, you know to slow down before you run out before market day.

*(Grown-up translation: quota monitoring on Databricks Free Edition — since
there's no dollar bill, you watch compute/storage/job quota instead.)*

---

## Why We Did All This

So that no matter *who* asks about the lemonade — a friend, a customer, or
the genie — they always get the **same true answer**, because everyone is
reading from the **same one recipe card**, kept safe in a box that only the
Recipe Keeper can update, checked by a grown-up before it's trusted, with a
notebook that remembers who looked at it.

That's the whole idea. Everything else is just making that work for a
bigger stand, with more friends, and more recipes.
