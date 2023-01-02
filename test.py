import datetime

from glowmarkt import BrightClient

glowmarkt = BrightClient("aniket.garg@hotmail.com", "^c&d6ZUTXkcK#2Cw")

# ents = cli.get_virtual_entities()

# for ent in ents:
#     print("Entity:", ent.name)
#     for res in ent.get_resources():
#         print("  %s:" % res.name)

# print(cli.token)

# cli = BrightClient("aniket.garg@hotmail.com", "^c&d6ZUTXkcK#2C")

virtual_entities: dict = {}
resources: dict = {}

virtual_entities = glowmarkt.get_virtual_entities()

for virtual_entity in virtual_entities:
    resources = virtual_entity.get_resources()
    for resource in resources:
        print(resource.classifier)
        tariff = resource.get_tariff()
        t_from = datetime.datetime.now() - datetime.timedelta(minutes=60)
        t_to = datetime.datetime.now()
        period = "PT30M"
        t_from = resource.round(t_from, period)
        t_to = resource.round(t_to, period)
        rdgs = resource.get_readings(t_from, t_to, period, func="sum", nulls=True)
        for r in rdgs:
            print("    %s: %s" % (r[0].astimezone().replace(tzinfo=None), r[1]))
        # print("    %s: %s" % (rdgs[0][0].astimezone().replace(tzinfo=None), rdgs[0][1]))
        # print(rdgs[0][1].value)
