---
title: Sources
---

# Sources

The index is built from the following sources:

<ul>
    {% for source in site.data.sources %}
        <li>
            {% if source.html_url %}<a href="{{ source.html_url }}">{% endif %}
            {% if source.name %}{{ source.name }}{% else %}{{ source.path }}{% endif %}
            {% if source.html_url %}</a>{% endif %}
            <div>{{ source.description | strip_html }}</div>
        </li>
    {% endfor %}
</ul>
