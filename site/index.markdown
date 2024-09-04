---
title: Library
layout: full
---

# Library

<ul class="applications">
    {% for application in site.data.library %}
        <li>
            <div class="application-header">
                <div class="application-name">
                    {% if application.iconData %}
                        <img class="icon" src="{{ application.iconData }}">
                    {% endif %}
                    {{ application.name }}
                </div>
                <div class="application-identifier">
                    {{ application.uid | truncate: 10 }}
                </div>
            </div>
            {% if application.summary %}
                <div class="summary">
                    <p>{{ application.summary }}</p>
                </div>
            {% endif %}
            {% if application.tags.size > 0 %}
                <ul class="tags">
                {% for tag in application.tags %}
                    <li class="{{ tag }}">{{ tag }}</li>
                {% endfor %}
                </ul>
            {% endif %}
            {% if application.screenshots %}
                <div class="screenshots">
                    {% for screenshot in application.screenshots %}
                        <img class="screenshot" src="{{ screenshot }}" />
                    {% endfor %}
                </div>
            {% endif %}
            {% if application.readme %}
                <details class="readme">
                    <summary>Readme</summary>
                    <div class="readme-contents">{{ application.readme | xml_escape }}</div>
                </details>
            {% endif %}
            {% for version in application.versions %}
                <div class="version-header">
                    <div class="version-name">
                        {{ version.version }}
                    </div>
                    <div class="version-details">
                        {% if version.variants.size > 1 %}
                            {{ version.variants.size }} variants
                        {% endif %}
                    </div>
                </div>
                <ul>
                    {% for variant in version.variants %}
                        <li>
                            {% for installer in variant.items %}
                                <div class="path">
                                    {% for component in installer.reference %}
                                        {% if component.url %}<a href="{{ component.url }}">{% endif %}{{ component.name | xml_escape }}{% if component.url %}</a>{% endif %}
                                        {% if forloop.last == false %}
                                            &#8594;
                                        {% endif %}
                                    {% endfor %}
                                </div>
                            {% endfor %}
                        </li>
                    {% endfor %}
                </ul>
            {% endfor %}
        </li>
    {% endfor %}
</ul>
