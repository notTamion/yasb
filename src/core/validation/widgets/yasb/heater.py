DEFAULTS = {
    'label': "{volume[percent]}%",
    'label_alt': "{volume[percent]}%",
    'heater_icon': "\udb86\ude45",
    'callbacks': {
        'on_middle': 'do_nothing',
        'on_right': 'do_nothing'
    },
}

VALIDATION_SCHEMA = {
    'label': {
        'type': 'string',
        'default': DEFAULTS['label']
    },
    'label_alt': {
        'type': 'string',
        'default': DEFAULTS['label_alt']
    },
    'heater_icon': {
        'type': 'string',
        'default': DEFAULTS['heater_icon'],
        'required': False
    },
    'callbacks': {
        'type': 'dict',
        'schema': {
            'on_middle': {
                'type': 'string',
                'default': DEFAULTS['callbacks']['on_middle'],
            },
            'on_right': {
                'type': 'string',
                'default': DEFAULTS['callbacks']['on_right'],
            }
        },
        'default': DEFAULTS['callbacks']
    }
}
