---
title: Index
---

# Index

## EPOC32

<ul>
    {% for program in site.data.programs %}
        {% if program.tags contains "epoc32" %}
            <li><a href="/programs/{{ program.uid }}">{{ program.name }}</a></li>
        {% endif %}
    {% endfor %}
</ul>

## SIBO

<ul>
    {% for program in site.data.programs %}
        {% if program.tags contains "sibo" %}
            <li><a href="/programs/{{ program.uid }}">{{ program.name }}</a></li>
        {% endif %}
    {% endfor %}
</ul>

## Unknown

<ul>
    {% for program in site.data.programs %}
        {% if program.tags contains "epoc32" %}
        {% elsif program.tags contains "sibo" %}
        {% else %}
            <li><a href="/programs/{{ program.uid }}">{{ program.name }}</a></li>
        {% endif %}
    {% endfor %}
</ul>