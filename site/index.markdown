---
title: Library
layout: full
---

# Psion Software Index

<ul class="applications">{% for program in site.data.programs %}<li><a href="/programs/{{ program.uid }}">{% if program.icon %}<img class="icon" width="{{ program.icon.width }}" height="{{ program.icon.height }}" src="/{{ program.icon.path }}">{% else %}<img class="icon" width="48" height="48" src="/images/unknown.gif">{% endif %}{{ program.name }}</a></li>{% endfor %}</ul>
