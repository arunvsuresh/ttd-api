import json

from ttdclient.models.base import Base
from ttdclient.models.site_list import SiteList
from ttdclient.models.campaign import Campaign

class AdGroup(Base):

    obj_name = "adgroup"

    def getId(self):
        return self.get("AdGroupId")

    def get_by_campaign(self, campaign_id):
        payload = { "CampaignId": campaign_id,
                    "PageStartIndex": 0,
                    "PageSize": None }
        method = "POST"
        url = '{0}/{1}'.format(self.get_url(), 'query/campaign')
        
        response = self._execute(method, url, json.dumps(payload))
        return self._get_response_objects(response)


    def get_by_name(self, campaign_id, name):
        payload = { "CampaignId": campaign_id,
                    "SearchTerms": [name],
                    "PageStartIndex": 0,
                    "PageSize": None }
        method = "POST"
        url = '{0}/{1}'.format(self.get_url(), 'query/campaign')
        
        response = self._execute(method, url, json.dumps(payload))
        return self._get_response_objects(response)

    def set_deals(self, deal_ids=None, deal_group_ids=None):

        if 'RTBAttributes' not in self:
            self['RTBAttributes'] = {}

        if deal_ids is None:
            deal_ids = []

        if deal_group_ids is None:
            deal_group_ids = []

        adjustments = self['RTBAttributes'].get('ContractTargeting', {}).get('ContractAdjustments')

        self['RTBAttributes']['ContractTargeting'] = { 
            #'ContractIds': deal_ids,
            'ContractGroupIds': deal_group_ids
            }

        new_adjustments = []
        if adjustments and len(adjustments) > 0:
            for adjustment in adjustments:
                if adjustment['Id'] in deal_ids:
                    deal_ids.remove(adjustment['Id'])
                    new_adjustments.append(adjustment)

            for deal_id in deal_ids:
                new_adjustments.append({"Adjustment": 1.0, "Id": deal_id})

            self['RTBAttributes']['ContractTargeting']['ContractAdjustments'] = new_adjustments
        else:
            self['RTBAttributes']['ContractTargeting']['ContractIds'] = deal_ids

    def set_delivery_profile_adjustments(self, deal_ids=None):

        if 'RTBAttributes' not in self:
            self['RTBAttributes'] = {}

        if deal_ids is None:
            deal_ids = []
        else:
            delivery_profile_adjustments = []
            for deal_id in deal_ids:
                val = {}
                val["Id"] = deal_id
                val["Adjustment"] = 1
                delivery_profile_adjustments.append(val)

        self['RTBAttributes']['ContractTargeting'] = { 
            'AllowOpenMarketBiddingWhenTargetingContracts': False,
            'ContractIds': [],
            'ContractGroupIds': [],
            'ContractAdjustments': [],
            "DeliveryProfileAdjustments": delivery_profile_adjustments
            }

    """
    def set_deal_groups(self, deal_group_ids):

        if 'RTBAttributes' not in self:
            self['RTBAttributes'] = {}
            
        self['RTBAttributes']['ContractTargeting'] = { 
            'AllowOpenMarketBiddingWhenTargetingContracts': True,
            'ContractGroupIds': deal_group_ids
            }
    """

    def target_exchanges(self, target=False):

        if 'RTBAttributes' not in self:
            self['RTBAttributes'] = {}
            
        if 'ContractTargeting' not in self['RTBAttributes']:
            return None

        if 'ContractIds' not in self['RTBAttributes']['ContractTargeting']:
            return None

        self['RTBAttributes']['ContractTargeting']['AllowOpenMarketBiddingWhenTargetingContracts'] = target

    def get_deals(self):

        if 'RTBAttributes' not in self:
            return None
            
        if 'ContractTargeting' not in self['RTBAttributes']:
            return None

        if 'ContractIds' not in self['RTBAttributes']['ContractTargeting']:
            return None

        return self['RTBAttributes']['ContractTargeting']['ContractIds']

    def get_deal_groups(self):

        if 'RTBAttributes' not in self:
            return None
            
        if 'ContractTargeting' not in self['RTBAttributes']:
            return None

        if 'ContractGroupIds' not in self['RTBAttributes']['ContractTargeting']:
            return None

        return self['RTBAttributes']['ContractTargeting']['ContractGroupIds']

    def get_creatives(self):

        if 'RTBAttributes' not in self:
            return None
            
        return self['RTBAttributes'].get('CreativeIds', None)


    def set_exchanges(self, exchange_ids, override=True):

        if 'RTBAttributes' not in self:
            self['RTBAttributes'] = {}
            
        self['RTBAttributes']['SupplyVendorAdjustments']['DefaultAdjustment'] = 0.0 
    
        if override or 'Adjustments' not in self['RTBAttributes']['SupplyVendorAdjustments']:
            self['RTBAttributes']['SupplyVendorAdjustments']['Adjustments'] = []

        for id in exchange_ids:

            # Default
            adjustment = 1.0

            # If we get a 'Bid Adjustment' from TTD, use it instead of the default
            for x in self['RTBAttributes'].get('SupplyVendorAdjustments').get('Adjustments'):
                if int(x.get('Id')) == int(id):
                    adjustment = x.get('Adjustment')

            self['RTBAttributes']['SupplyVendorAdjustments']['Adjustments'].append({'Id': id, 'Adjustment': adjustment})


    def set_domains(self, domains, sitelist_id=None):

        # get the campaign so we can get the advertiserId
        loader = Campaign(Base.connection)
        campaign = loader.find(self['CampaignId'])

        # get the sitelist
        loader = SiteList(Base.connection)
        if sitelist_id is not None:
            sitelist = loader.find(sitelist_id)
        else:
            sitelist = loader.find_by_name(campaign['AdvertiserId'], self['AdGroupName'])

        if sitelist == None:
            sitelist = SiteList(Base.connection)
            sitelist['SiteListName'] = self['AdGroupName']
            sitelist['AdvertiserId'] = campaign['AdvertiserId']

        sitelist.set_domains(domains)
        if sitelist.getId() == 0 or sitelist.getId() is None:
            sitelist.create()
        else:
            sitelist.save()

        if 'RTBAttributes' not in self:
            self['RTBAttributes'] = {}

        # sitelist.getId() always exists so set as default list
        if 'SiteTargeting' in self['RTBAttributes']:
            # If Ad Group as a current list, use it and append the new ID.
            if 'SiteListIds' in self['RTBAttributes']['SiteTargeting']:
                currentList = self['RTBAttributes']['SiteTargeting']['SiteListIds']

                # Weird error if duplicate IDs exist
                """
                Exception: Bad response code {"Message":"The request failed validation. Please check your request and try again.","ErrorDetails":[{"Property":"AdGroup.RTBAttributes.SiteTargeting.SiteListIds","Reasons":["The following Site Lists cannot be used for this operation because they are not accessible to Advertiser '9ut3ufp': ."]}]}
                """
                if sitelist.getId() not in currentList:
                    currentList.append(sitelist.getId())
        else:
            currentList = [sitelist.getId()]

        if len(domains) == 0 and sitelist.getId() in currentList:
            currentList.remove(sitelist.getId())

        if len(currentList) == 0:
            self['RTBAttributes']['SiteTargeting'] = {
                'SiteListIds': [],
                'SiteListFallThroughAdjustment': 1
                }
        else:
            self['RTBAttributes']['SiteTargeting'] = {
                'SiteListIds': currentList,
                'SiteListFallThroughAdjustment': 0
                }

        return sitelist.getId()

    def set_budget(self, budget, currency_code):
        if 'RTBAttributes' not in self:
            self['RTBAttributes'] = {}
            
        if 'BudgetSettings' not in self['RTBAttributes']:
            self['RTBAttributes']['BudgetSettings'] = {}

        if 'Budget' not in self['RTBAttributes']['BudgetSettings']:
            self['RTBAttributes']['BudgetSettings']['Budget'] = {'CurrencyCode': currency_code}
        
        self['RTBAttributes']['BudgetSettings']['Budget']['Amount'] = budget
        
