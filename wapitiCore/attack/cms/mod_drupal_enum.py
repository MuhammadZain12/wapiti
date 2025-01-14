import json
from typing import Optional
from httpx import RequestError

from wapitiCore.net import Request
from wapitiCore.attack.cms.cms_common import CommonCMS, MSG_TECHNO_VERSIONED
from wapitiCore.net.response import Response
from wapitiCore.definitions.fingerprint_webapp import NAME as WEB_APP_VERSIONED, WSTG_CODE as WEB_WSTG_CODE
from wapitiCore.definitions.fingerprint import NAME as TECHNO_DETECTED, WSTG_CODE
from wapitiCore.main.log import log_blue, logging

MSG_NO_DRUPAL = "No Drupal Detected"


class ModuleDrupalEnum(CommonCMS):
    """Detect Drupal version."""
    PAYLOADS_HASH = "drupal_hash_files.json"

    versions = []

    async def check_drupal(self, url):
        check_list = ['core/misc/drupal.js', 'misc/drupal.js']
        for item in check_list:
            request = Request(f'{url}{item}', 'GET')
            try:
                response: Response = await self.crawler.async_send(request, follow_redirects=True)
            except RequestError:
                self.network_errors += 1
            except Exception as exception:
                logging.exception(exception)
            else:
                if (
                    response.is_success
                    and "content-type" in response.headers
                    and "application/javascript" in response.headers["content-type"]
                   ):
                    return True
        return False

    async def must_attack(self, request: Request, response: Optional[Response] = None):
        if self.finished:
            return False

        if request.method == "POST":
            return False

        return request.url == await self.persister.get_root_url()

    async def attack(self, request: Request, response: Optional[Response] = None):
        self.finished = True
        request_to_root = Request(request.url)

        if await self.check_drupal(request_to_root.url):
            await self.detect_version(self.PAYLOADS_HASH, request_to_root.url)  # Call the method on the instance
            self.versions = sorted(self.versions, key=lambda x: x.split('.')) if self.versions else []

            drupal_detected = {
                "name": "Drupal",
                "versions": self.versions,
                "categories": ["CMS Drupal"],
                "groups": ["Content"]
            }

            log_blue(
                MSG_TECHNO_VERSIONED,
                "Drupal",
                self.versions
            )

            if self.versions:
                await self.add_vuln_info(
                    category=WEB_APP_VERSIONED,
                    request=request_to_root,
                    info=json.dumps(drupal_detected),
                    wstg=WEB_WSTG_CODE
                )
            await self.add_addition(
                category=TECHNO_DETECTED,
                request=request_to_root,
                info=json.dumps(drupal_detected),
                wstg=WSTG_CODE
            )
        else:
            log_blue(MSG_NO_DRUPAL)
